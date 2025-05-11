#!/usr/bin/env python3
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, split, to_date, 
    date_format, count, avg, stddev, 
    regexp_replace, lower, lit
)
from pyspark.ml.feature import StopWordsRemover, CountVectorizer, IDF
from textblob import TextBlob
import os
import json
import boto3
import logging
import argparse
from datetime import datetime, timedelta
from pyspark.sql.types import FloatType, ArrayType, StringType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# UDF for sentiment analysis
def analyze_sentiment(text):
    if text is None:
        return 0.0
    try:
        return TextBlob(text).sentiment.polarity
    except:
        return 0.0

def extract_keywords(spark, df, subreddit, output_path, s3_client, bucket_name):
    """Extract top keywords from posts in a subreddit"""
    logger.info(f"Extracting keywords for subreddit: {subreddit}")
    
    # Preprocess text
    words_df = df.withColumn(
        "words", 
        split(regexp_replace(lower(col("text")), r"[^a-zA-Z\s]", " "), " ")
    )
    
    # Remove stop words
    remover = StopWordsRemover(
        inputCol="words", 
        outputCol="filtered_words"
    )
    words_df = remover.transform(words_df)
    
    # Create term frequency vectors
    cv = CountVectorizer(
        inputCol="filtered_words", 
        outputCol="tf", 
        minDF=5.0
    )
    cv_model = cv.fit(words_df)
    tf_df = cv_model.transform(words_df)
    
    # Create IDF vectors
    idf = IDF(inputCol="tf", outputCol="tf_idf")
    idf_model = idf.fit(tf_df)
    tfidf_df = idf_model.transform(tf_df)
    
    # Get vocabulary
    vocab = cv_model.vocabulary
    
    # Calculate average TF-IDF for each term
    from pyspark.ml.linalg import Vectors, VectorUDT
    from pyspark.sql.functions import udf
    from pyspark.sql.types import ArrayType, FloatType, StructType, StructField, StringType
    
    def extract_weights(vector):
        return [(i, float(weight)) for i, weight in zip(vector.indices, vector.values)]
    
    extract_weights_udf = udf(extract_weights, ArrayType(
        StructType([
            StructField("idx", StringType()),
            StructField("weight", FloatType())
        ])
    ))
    
    weights_df = tfidf_df.withColumn("weights", extract_weights_udf("tf_idf"))
    weights_df = weights_df.select("weights")
    weights_df = weights_df.withColumn("weight_items", explode("weights"))
    weights_df = weights_df.select(
        col("weight_items.idx").cast("int").alias("idx"),
        col("weight_items.weight").alias("weight")
    )
    
    # Group by term index and calculate average weight
    agg_weights = weights_df.groupBy("idx").agg(
        avg("weight").alias("avg_weight")
    ).orderBy(col("avg_weight").desc())
    
    # Get top 50 keywords
    top_keywords = agg_weights.limit(50)
    
    # Convert to list of (term, weight) pairs
    keyword_list = top_keywords.rdd.map(
        lambda row: (vocab[row["idx"]], float(row["avg_weight"]))
    ).collect()
    
    # Create three timeframes: daily, weekly, monthly
    daily_keywords = [{"keyword": k, "weight": w, "timeframe": "daily", "subreddit": subreddit} 
                     for k, w in keyword_list[:20]]
    weekly_keywords = [{"keyword": k, "weight": w, "timeframe": "weekly", "subreddit": subreddit} 
                      for k, w in keyword_list[:30]]
    monthly_keywords = [{"keyword": k, "weight": w, "timeframe": "monthly", "subreddit": subreddit} 
                       for k, w in keyword_list]
    
    # Write to local JSON files
    daily_path = os.path.join(output_path, f"{subreddit}_daily_keywords.json")
    weekly_path = os.path.join(output_path, f"{subreddit}_weekly_keywords.json")
    monthly_path = os.path.join(output_path, f"{subreddit}_monthly_keywords.json")
    
    with open(daily_path, 'w') as f:
        json.dump(daily_keywords, f)
    with open(weekly_path, 'w') as f:
        json.dump(weekly_keywords, f)
    with open(monthly_path, 'w') as f:
        json.dump(monthly_keywords, f)
    
    # Upload to S3/MinIO
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"analytics/keywords/{subreddit}/daily",
        Body=json.dumps(daily_keywords)
    )
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"analytics/keywords/{subreddit}/weekly",
        Body=json.dumps(weekly_keywords)
    )
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"analytics/keywords/{subreddit}/monthly",
        Body=json.dumps(monthly_keywords)
    )

def analyze_sentiment_trends(spark, df, subreddit, output_path, s3_client, bucket_name):
    """Analyze sentiment trends over time for a subreddit"""
    logger.info(f"Analyzing sentiment for subreddit: {subreddit}")
    
    # Register sentiment UDF
    sentiment_udf = spark.udf.register("sentiment", analyze_sentiment, FloatType())
    
    # Calculate sentiment for each post
    df = df.withColumn("sentiment_score", sentiment_udf(col("text")))
    
    # Group by date and calculate average sentiment
    daily_sentiment = df.groupBy("created_date").agg(
        avg("sentiment_score").alias("sentiment_score")
    ).orderBy("created_date")
    
    # Convert to list of records
    sentiment_data = daily_sentiment.rdd.map(
        lambda row: {
            "subreddit": subreddit,
            "date": row["created_date"].strftime("%Y-%m-%d"),
            "sentiment_score": float(row["sentiment_score"])
        }
    ).collect()
    
    # Write to local JSON file
    sentiment_path = os.path.join(output_path, f"{subreddit}_sentiment.json")
    with open(sentiment_path, 'w') as f:
        json.dump(sentiment_data, f)
    
    # Upload to S3/MinIO
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"analytics/sentiment_daily/{subreddit}",
        Body=json.dumps(sentiment_data)
    )

def get_subreddit_list(spark, s3_endpoint, s3_access_key, s3_secret_key, bucket_name, prefix):
    """Get list of available subreddits"""
    # Configure S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint,
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key,
        verify=False,
    )
    
    # List objects in bucket with prefix
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix,
        Delimiter='/'
    )
    
    subreddits = []
    if 'CommonPrefixes' in response:
        for obj in response['CommonPrefixes']:
            # Extract subreddit name from prefix
            subreddit = obj['Prefix'].split('/')[-2]
            subreddits.append(subreddit)
    
    return subreddits

def main():
    parser = argparse.ArgumentParser(description="Generate analytics from subreddit data")
    parser.add_argument(
        "--output-dir",
        default="/data/analytics",
        help="Directory to save analytics data",
    )
    parser.add_argument(
        "--s3-bucket",
        default="mh-trends",
        help="S3/MinIO bucket name",
    )
    parser.add_argument(
        "--s3-raw-prefix",
        default="raw",
        help="S3/MinIO prefix for raw data",
    )
    parser.add_argument(
        "--s3-endpoint",
        default="http://minio:9000",
        help="S3/MinIO endpoint URL",
    )
    parser.add_argument(
        "--s3-access-key",
        default="minioadmin",
        help="S3/MinIO access key",
    )
    parser.add_argument(
        "--s3-secret-key",
        default="minioadmin",
        help="S3/MinIO secret key",
    )
    parser.add_argument(
        "--subreddits", 
        nargs="*", 
        help="List of subreddits to analyze (defaults to all)"
    )
    
    args = parser.parse_args()
    
    # Create Spark session with necessary packages
    spark = SparkSession.builder \
        .appName("Subreddit Data Analytics") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.1") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.endpoint", args.s3_endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", args.s3_access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", args.s3_secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl.disable.cache", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Configure S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=args.s3_endpoint,
        aws_access_key_id=args.s3_access_key,
        aws_secret_access_key=args.s3_secret_key,
        verify=False,
    )
    
    try:
        # Get list of subreddits if not provided
        if not args.subreddits:
            args.subreddits = get_subreddit_list(
                spark, 
                args.s3_endpoint, 
                args.s3_access_key, 
                args.s3_secret_key,
                args.s3_bucket,
                args.s3_raw_prefix
            )
        
        # Save list of subreddits for API
        s3_client.put_object(
            Bucket=args.s3_bucket,
            Key="analytics/subreddits",
            Body=json.dumps(args.subreddits)
        )
        
        # Process each subreddit
        for subreddit in args.subreddits:
            logger.info(f"Processing analytics for subreddit: {subreddit}")
            
            # Read data from S3/MinIO
            s3_path = f"s3a://{args.s3_bucket}/{args.s3_raw_prefix}/{subreddit}"
            df = spark.read.parquet(s3_path)
            
            # Extract keywords
            extract_keywords(spark, df, subreddit, args.output_dir, s3_client, args.s3_bucket)
            
            # Analyze sentiment
            analyze_sentiment_trends(spark, df, subreddit, args.output_dir, s3_client, args.s3_bucket)
        
        # Create a placeholder events dataset
        events_data = [
            {"date": "2023-01-15", "event": "Major platform update announced", "category": "technology"},
            {"date": "2023-02-28", "event": "Content policy changes", "category": "policy"},
            {"date": "2023-03-22", "event": "Server outage", "category": "infrastructure"},
            {"date": "2023-04-01", "event": "April Fools experiment", "category": "social"},
            {"date": "2023-05-15", "event": "API pricing changes", "category": "business"}
        ]
        s3_client.put_object(
            Bucket=args.s3_bucket,
            Key="analytics/events",
            Body=json.dumps(events_data)
        )
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 