#!/usr/bin/env python3
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, explode, array, collect_list, row_number,
    from_unixtime, unix_timestamp, date_format, year, month, quarter,
    udf, pandas_udf, PandasUDFType, count, struct, to_json
)
from pyspark.sql.types import (
    StringType, ArrayType, StructType, StructField, 
    FloatType, MapType, Row
)
import argparse
import os
import boto3
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from keybert import KeyBERT
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define schema for keyword results
keywords_schema = ArrayType(
    StructType([
        StructField("keyword", StringType(), True),
        StructField("weight", FloatType(), True)
    ])
)

# Define pandas UDF for KeyBERT keyword extraction
@pandas_udf(keywords_schema, PandasUDFType.SCALAR_ITER)
def extract_keywords_udf(content_series_iter):
    """
    Extract keywords from texts using KeyBERT.
    Takes batches of texts and returns extracted keywords with weights.
    """
    # Initialize KeyBERT model (this happens once per partition)
    model = KeyBERT()
    
    # Process each batch
    for content_series in content_series_iter:
        results = []
        
        for text in content_series:
            if text is None or text == "" or len(text) < 20:
                results.append([])
                continue
                
            try:
                # Extract top 10 keywords
                keywords = model.extract_keywords(
                    text, 
                    keyphrase_ngram_range=(1, 2),
                    stop_words='english',
                    use_mmr=True,
                    diversity=0.7,
                    top_n=10
                )
                
                # Convert to required format
                keyword_list = [{"keyword": kw, "weight": score} for kw, score in keywords]
                results.append(keyword_list)
                
            except Exception as e:
                logger.warning(f"Error extracting keywords: {str(e)}")
                results.append([])
                
        yield pd.Series(results)

def extract_keywords_by_timeframe(spark, input_path, output_path, content_type, timeframe):
    """Extract keywords by specified timeframe"""
    logger.info(f"Extracting keywords for {content_type} from {input_path} by {timeframe}")
    
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
    
    # Add timeframe columns
    df = df.withColumn("year", year(col("date")))
    df = df.withColumn("month", month(col("date")))
    df = df.withColumn("quarter", quarter(col("date")))
    
    # Group by timeframe
    if timeframe == "monthly":
        group_cols = ["subreddit", "year", "month"]
        timeframe_col = concat_ws("-", col("year"), lpad(col("month"), 2, "0"))
    elif timeframe == "quarterly":
        group_cols = ["subreddit", "year", "quarter"]
        timeframe_col = concat_ws("Q", col("year"), col("quarter"))
    elif timeframe == "yearly":
        group_cols = ["subreddit", "year"]
        timeframe_col = col("year").cast(StringType())
    else:  # all time
        group_cols = ["subreddit"]
        timeframe_col = lit("all")
    
    # Add timeframe column
    df = df.withColumn("timeframe", timeframe_col)
    
    # Concatenate all texts by group
    text_by_group = df.groupBy(group_cols + ["timeframe"]).agg(
        concat_ws(" ", collect_list("text_content")).alias("combined_text"),
        count("*").alias("post_count")
    )
    
    # Filter out groups with too few posts
    text_by_group = text_by_group.filter(col("post_count") >= 10)
    
    # Extract keywords
    keywords_df = text_by_group.withColumn(
        "keywords", extract_keywords_udf(col("combined_text"))
    )
    
    # Explode the keywords array
    exploded_df = keywords_df.select(
        "subreddit", "timeframe", "post_count", explode(col("keywords")).alias("keyword_struct")
    )
    
    # Extract keyword and weight
    final_df = exploded_df.select(
        "subreddit", 
        "timeframe", 
        "post_count",
        col("keyword_struct.keyword").alias("keyword"),
        col("keyword_struct.weight").alias("weight")
    )
    
    # Write results
    logger.info(f"Writing keyword results to {output_path}")
    final_df.write.mode("overwrite").parquet(output_path)
    
    return final_df

def upload_to_s3(spark, data_df, s3_bucket, s3_key):
    """Upload processed keyword data to S3"""
    # Configure S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    
    # Group data by subreddit and timeframe
    subreddits = data_df.select("subreddit").distinct().collect()
    timeframes = data_df.select("timeframe").distinct().collect()
    
    for subreddit_row in subreddits:
        subreddit = subreddit_row["subreddit"]
        
        for timeframe_row in timeframes:
            timeframe = timeframe_row["timeframe"]
            
            # Filter data for this subreddit and timeframe
            filtered_data = data_df.filter(
                (col("subreddit") == subreddit) & 
                (col("timeframe") == timeframe)
            ).orderBy(col("weight").desc())
            
            # Take top 20 keywords
            top_keywords = filtered_data.limit(20)
            
            # Convert to list of dicts for JSON serialization
            keywords_list = top_keywords.toPandas().to_dict(orient="records")
            
            # Write to JSON
            json_data = json.dumps(keywords_list)
            
            # Upload to S3
            s3_key_path = f"{s3_key}/{subreddit}/{timeframe}"
            logger.info(f"Uploading keyword data for r/{subreddit} ({timeframe}) to s3://{s3_bucket}/{s3_key_path}")
            
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key_path,
                Body=json_data
            )

def main():
    parser = argparse.ArgumentParser(description="Extract keywords from Reddit data")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing cleaned Reddit Parquet files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save processed keyword Parquet files",
    )
    parser.add_argument(
        "--content-type",
        choices=["submissions", "comments", "all"],
        default="submissions",
        help="Content type to process (default: submissions)",
    )
    parser.add_argument(
        "--timeframe",
        choices=["monthly", "quarterly", "yearly", "all"],
        default="monthly",
        help="Timeframe for keyword aggregation (default: monthly)",
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
        default="analytics/keywords",
        help="S3 key prefix (default: analytics/keywords)",
    )
    
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Keyword Extraction") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        if args.content_type in ["submissions", "all"]:
            submissions_input = os.path.join(args.input_dir, "submissions")
            submissions_output = os.path.join(args.output_dir, f"submissions_{args.timeframe}")
            
            submissions_keywords_df = extract_keywords_by_timeframe(
                spark, submissions_input, submissions_output, "submissions", args.timeframe
            )
            
            if args.upload_to_s3:
                upload_to_s3(
                    spark,
                    submissions_keywords_df,
                    args.s3_bucket,
                    f"{args.s3_key_prefix}/submissions/{args.timeframe}"
                )
        
        if args.content_type in ["comments", "all"]:
            comments_input = os.path.join(args.input_dir, "comments")
            comments_output = os.path.join(args.output_dir, f"comments_{args.timeframe}")
            
            comments_keywords_df = extract_keywords_by_timeframe(
                spark, comments_input, comments_output, "comments", args.timeframe
            )
            
            if args.upload_to_s3:
                upload_to_s3(
                    spark,
                    comments_keywords_df,
                    args.s3_bucket,
                    f"{args.s3_key_prefix}/comments/{args.timeframe}"
                )
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 