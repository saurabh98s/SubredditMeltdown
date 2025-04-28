#!/usr/bin/env python3
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, lit, date_format, to_date, avg, count, 
    from_unixtime, unix_timestamp, explode, array, 
    udf, pandas_udf, PandasUDFType
)
from pyspark.sql.types import FloatType, ArrayType, StringType, StructType, StructField
import argparse
import os
import boto3
import json
import logging
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize NLTK resources (download if needed)
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

# Define a pandas UDF for VADER sentiment analysis
@pandas_udf(FloatType())
def analyze_sentiment(texts):
    """
    Analyze sentiment of texts using VADER SentimentIntensityAnalyzer.
    Returns a sentiment score between -1 (negative) and 1 (positive).
    """
    vader = SentimentIntensityAnalyzer()
    
    def get_sentiment(text):
        if text is None or text == "" or text == "[deleted]" or text == "[removed]":
            return None
        try:
            scores = vader.polarity_scores(text)
            # Compound score is between -1 and 1
            return scores['compound']
        except:
            return None
    
    return pd.Series([get_sentiment(text) for text in texts])

def calculate_daily_sentiment(spark, input_path, output_path, content_type):
    """Calculate daily average sentiment per subreddit"""
    logger.info(f"Calculating daily sentiment for {content_type} from {input_path}")
    
    # Read parquet files
    df = spark.read.parquet(input_path)
    
    # Select text column based on content type
    if content_type == "submissions":
        text_col = "selftext"
        title_col = "title"
        # For submissions, use both title and selftext
        df = df.withColumn("text_content", 
                          when(col("selftext").isNull() | 
                               (col("selftext") == "") | 
                               (col("selftext") == "[deleted]") | 
                               (col("selftext") == "[removed]"),
                               col("title")).otherwise(
                                   col("title") + " " + col("selftext")
                               ))
    else:  # comments
        text_col = "body"
        df = df.withColumn("text_content", col(text_col))
    
    # Convert UTC timestamp to date
    df = df.withColumn(
        "date", 
        date_format(
            from_unixtime(unix_timestamp(col("created_utc"))),
            "yyyy-MM-dd"
        )
    )
    
    # Calculate sentiment scores
    df = df.withColumn("sentiment_score", analyze_sentiment(col("text_content")))
    
    # Group by subreddit and date, calculate average sentiment
    daily_sentiment = df.groupBy("subreddit", "date").agg(
        avg("sentiment_score").alias("avg_sentiment"),
        count("*").alias("post_count")
    )
    
    # Filter out days with too few posts for statistical significance
    daily_sentiment = daily_sentiment.filter(col("post_count") >= 5)
    
    # Write results
    logger.info(f"Writing daily sentiment results to {output_path}")
    daily_sentiment.write.mode("overwrite").parquet(output_path)
    
    return daily_sentiment

def upload_to_s3(spark, data_df, s3_bucket, s3_key):
    """Upload processed sentiment data to S3"""
    # Configure S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    
    # Group data by subreddit
    subreddits = data_df.select("subreddit").distinct().collect()
    
    for subreddit_row in subreddits:
        subreddit = subreddit_row["subreddit"]
        
        # Filter data for this subreddit
        subreddit_data = data_df.filter(col("subreddit") == subreddit).orderBy("date")
        
        # Convert to list of dicts for JSON serialization
        subreddit_data_list = subreddit_data.toPandas().to_dict(orient="records")
        
        # Write to JSON
        json_data = json.dumps(subreddit_data_list)
        
        # Upload to S3
        s3_key_path = f"{s3_key}/{subreddit}"
        logger.info(f"Uploading sentiment data for r/{subreddit} to s3://{s3_bucket}/{s3_key_path}")
        
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key_path,
            Body=json_data
        )

def main():
    parser = argparse.ArgumentParser(description="Calculate daily sentiment from Reddit data")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing cleaned Reddit Parquet files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save processed sentiment Parquet files",
    )
    parser.add_argument(
        "--content-type",
        choices=["submissions", "comments", "all"],
        default="all",
        help="Content type to process (default: all)",
    )
    parser.add_argument(
        "--upload-to-s3",
        action="store_true",
        help="Upload processed data to S3",
    )
    parser.add_argument(
        "--s3-bucket",
        default="mh-trends",
        help="S3 bucket name (default: mh-trends)",
    )
    parser.add_argument(
        "--s3-key-prefix",
        default="analytics/sentiment_daily",
        help="S3 key prefix (default: analytics/sentiment_daily)",
    )
    
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Sentiment Analysis") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()
    
    # Create output directories
    submissions_output = os.path.join(args.output_dir, "submissions_sentiment")
    comments_output = os.path.join(args.output_dir, "comments_sentiment")
    combined_output = os.path.join(args.output_dir, "combined_sentiment")
    os.makedirs(submissions_output, exist_ok=True)
    os.makedirs(comments_output, exist_ok=True)
    os.makedirs(combined_output, exist_ok=True)
    
    submissions_sentiment_df = None
    comments_sentiment_df = None
    
    try:
        # Process submissions
        if args.content_type in ["submissions", "all"]:
            submissions_input = os.path.join(args.input_dir, "submissions")
            submissions_sentiment_df = calculate_daily_sentiment(
                spark, submissions_input, submissions_output, "submissions"
            )
        
        # Process comments
        if args.content_type in ["comments", "all"]:
            comments_input = os.path.join(args.input_dir, "comments")
            comments_sentiment_df = calculate_daily_sentiment(
                spark, comments_input, comments_output, "comments"
            )
        
        # Combine submissions and comments sentiment (if both processed)
        if args.content_type == "all":
            # Union both dataframes
            combined_df = submissions_sentiment_df.unionByName(comments_sentiment_df)
            
            # Group by subreddit and date, recalculate weighted average
            combined_sentiment = combined_df.groupBy("subreddit", "date").agg(
                (sum(col("avg_sentiment") * col("post_count")) / sum(col("post_count"))).alias("avg_sentiment"),
                sum("post_count").alias("post_count")
            )
            
            # Write combined results
            logger.info(f"Writing combined sentiment results to {combined_output}")
            combined_sentiment.write.mode("overwrite").parquet(combined_output)
            
            # Upload to S3 if requested
            if args.upload_to_s3:
                upload_to_s3(
                    spark,
                    combined_sentiment,
                    args.s3_bucket,
                    args.s3_key_prefix
                )
        elif args.upload_to_s3:
            # Upload single content type if that's all that was processed
            if args.content_type == "submissions":
                upload_to_s3(
                    spark,
                    submissions_sentiment_df,
                    args.s3_bucket,
                    args.s3_key_prefix
                )
            elif args.content_type == "comments":
                upload_to_s3(
                    spark,
                    comments_sentiment_df,
                    args.s3_bucket,
                    args.s3_key_prefix
                )
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 