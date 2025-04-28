#!/usr/bin/env python3
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, lit, date_format, to_date, from_json, 
    avg, count, corr, sum, when, datediff, abs, 
    explode, array, map_from_entries
)
from pyspark.sql.types import StructType, StructField, StringType, FloatType, DateType, ArrayType
import argparse
import os
import boto3
import json
import logging
from datetime import datetime, timedelta
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define schema for events data
events_schema = StructType([
    StructField("date", StringType(), True),
    StructField("event", StringType(), True),
    StructField("category", StringType(), True),
    StructField("description", StringType(), True)
])

def load_events(spark, events_path):
    """Load events data from CSV file"""
    logger.info(f"Loading events data from {events_path}")
    
    events_df = spark.read.csv(events_path, header=True, schema=events_schema)
    
    # Convert date string to date type
    events_df = events_df.withColumn("date", to_date(col("date")))
    
    return events_df

def load_sentiment_data(spark, sentiment_path):
    """Load sentiment data from Parquet files"""
    logger.info(f"Loading sentiment data from {sentiment_path}")
    
    sentiment_df = spark.read.parquet(sentiment_path)
    
    # Convert date string to date type
    sentiment_df = sentiment_df.withColumn("date", to_date(col("date")))
    
    return sentiment_df

def correlate_sentiment_with_events(spark, sentiment_df, events_df, window_days=7):
    """
    Calculate correlation between sentiment changes and major events.
    Uses a sliding window approach around each event date.
    """
    logger.info(f"Correlating sentiment with events using {window_days}-day window")
    
    # Cross join to get all combinations of subreddits and events
    subreddits = sentiment_df.select("subreddit").distinct()
    cross_df = events_df.crossJoin(subreddits)
    
    # Define window functions
    windowSpec = Window.partitionBy("subreddit").orderBy("date")
    
    # Calculate daily sentiment change
    sentiment_with_change = sentiment_df.withColumn(
        "prev_sentiment", 
        lag(col("avg_sentiment"), 1).over(windowSpec)
    ).withColumn(
        "sentiment_change",
        col("avg_sentiment") - col("prev_sentiment")
    )
    
    # Join sentiment data with events
    results = []
    
    for subreddit_row in subreddits.collect():
        subreddit = subreddit_row["subreddit"]
        
        # Filter sentiment data for this subreddit
        subreddit_sentiment = sentiment_with_change.filter(col("subreddit") == subreddit)
        
        for event_row in events_df.collect():
            event_date = event_row["date"]
            event = event_row["event"]
            category = event_row["category"]
            
            # Get sentiment around event date
            before_window = event_date - timedelta(days=window_days)
            after_window = event_date + timedelta(days=window_days)
            
            # Get sentiment in window
            window_sentiment = subreddit_sentiment.filter(
                (col("date") >= before_window) & 
                (col("date") <= after_window)
            )
            
            if window_sentiment.count() == 0:
                continue
                
            # Calculate metrics
            before_event = window_sentiment.filter(col("date") < event_date)
            after_event = window_sentiment.filter(col("date") >= event_date)
            
            if before_event.count() == 0 or after_event.count() == 0:
                continue
                
            before_avg = before_event.agg(avg("avg_sentiment")).collect()[0][0]
            after_avg = after_event.agg(avg("avg_sentiment")).collect()[0][0]
            sentiment_diff = after_avg - before_avg
            
            # Calculate volatility change
            before_volatility = before_event.agg(stddev("sentiment_change")).collect()[0][0]
            after_volatility = after_event.agg(stddev("sentiment_change")).collect()[0][0]
            volatility_change = after_volatility - before_volatility
            
            # Add to results
            results.append({
                "subreddit": subreddit,
                "event_date": event_date.strftime("%Y-%m-%d"),
                "event": event,
                "category": category,
                "sentiment_before": float(before_avg) if before_avg else None,
                "sentiment_after": float(after_avg) if after_avg else None,
                "sentiment_diff": float(sentiment_diff) if sentiment_diff else None,
                "volatility_change": float(volatility_change) if volatility_change else None
            })
    
    # Convert to DataFrame
    result_df = spark.createDataFrame(results)
    
    return result_df

def upload_to_s3(data_df, s3_bucket, s3_key):
    """Upload correlation results to S3"""
    # Configure S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    
    # Convert to pandas for easier processing
    pd_df = data_df.toPandas()
    
    # Group by category
    for category in pd_df["category"].unique():
        category_df = pd_df[pd_df["category"] == category]
        
        # Group by subreddit
        for subreddit in category_df["subreddit"].unique():
            subreddit_df = category_df[category_df["subreddit"] == subreddit]
            
            # Sort by date
            subreddit_df = subreddit_df.sort_values("event_date")
            
            # Convert to JSON
            json_data = subreddit_df.to_json(orient="records")
            
            # Upload to S3
            s3_key_path = f"{s3_key}/{category}/{subreddit}"
            logger.info(f"Uploading correlation data for r/{subreddit} ({category}) to s3://{s3_bucket}/{s3_key_path}")
            
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key_path,
                Body=json_data
            )
    
    # Also upload events data
    events_json = pd_df[["event_date", "event", "category"]].drop_duplicates().to_json(orient="records")
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=f"{s3_key}/events",
        Body=events_json
    )

def main():
    parser = argparse.ArgumentParser(description="Correlate sentiment with major events")
    parser.add_argument(
        "--sentiment-path",
        required=True,
        help="Path to sentiment parquet files",
    )
    parser.add_argument(
        "--events-path",
        required=True,
        help="Path to events CSV file",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save correlation results",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Number of days before/after event to consider (default: 7)",
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
        default="analytics/events_correlation",
        help="S3 key prefix (default: analytics/events_correlation)",
    )
    
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Sentiment-Event Correlation") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Load data
        events_df = load_events(spark, args.events_path)
        sentiment_df = load_sentiment_data(spark, args.sentiment_path)
        
        # Calculate correlations
        correlation_df = correlate_sentiment_with_events(
            spark, sentiment_df, events_df, args.window_days
        )
        
        # Save results locally
        output_path = os.path.join(args.output_dir, "event_correlations")
        logger.info(f"Writing correlation results to {output_path}")
        correlation_df.write.mode("overwrite").parquet(output_path)
        
        # Upload to S3 if requested
        if args.upload_to_s3:
            upload_to_s3(
                correlation_df,
                args.s3_bucket,
                args.s3_key_prefix
            )
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 