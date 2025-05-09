#!/usr/bin/env python3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, lit, to_date, unix_timestamp
from pyspark.sql.types import StringType, StructType, StructField
import os
import glob
import boto3
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define schema for Reddit posts
post_schema = StructType([
    StructField("id", StringType(), True),
    StructField("title", StringType(), True),
    StructField("author", StringType(), True),
    StructField("created_utc", StringType(), True),
    StructField("text", StringType(), True),
    StructField("score", StringType(), True),
    StructField("num_comments", StringType(), True),
    StructField("url", StringType(), True),
])

def process_subreddit(spark, subreddit_path, output_base_path):
    """Process all data files for a single subreddit"""
    subreddit_name = os.path.basename(subreddit_path)
    logger.info(f"Processing subreddit: {subreddit_name}")
    
    # Find all data files in subreddit directory
    data_files = glob.glob(os.path.join(subreddit_path, "*.json"))
    
    if not data_files:
        logger.warning(f"No data files found for subreddit: {subreddit_name}")
        return None
    
    # Read all JSON files
    df = spark.read.json(data_files, schema=post_schema)
    
    # Add subreddit column
    df = df.withColumn("subreddit", lit(subreddit_name))
    
    # Convert created_utc to timestamp
    df = df.withColumn(
        "created_date", 
        to_date(unix_timestamp(col("created_utc")).cast("timestamp"))
    )
    
    # Clean and filter
    cleaned_df = df.filter(
        (col("text").isNotNull()) & 
        (col("text") != "[deleted]") & 
        (col("text") != "[removed]") &
        (col("author") != "[deleted]") &
        (col("author") != "AutoModerator")
    )
    
    # Output directory for this subreddit
    output_path = os.path.join(output_base_path, subreddit_name)
    
    # Write as parquet
    logger.info(f"Writing {cleaned_df.count()} posts for {subreddit_name} to {output_path}")
    cleaned_df.write.mode("overwrite").partitionBy("created_date").parquet(output_path)
    
    return output_path

def upload_to_minio(local_path, bucket_name, prefix):
    """Upload processed data to MinIO"""
    # Configure MinIO client
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        verify=False,
    )
    
    # Upload files
    for root, _, files in os.walk(local_path):
        for file in files:
            if file.endswith(".parquet") or file.endswith("_SUCCESS"):
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, local_path)
                s3_file_key = os.path.join(prefix, relative_path)
                
                logger.info(f"Uploading {local_file_path} to s3://{bucket_name}/{s3_file_key}")
                s3_client.upload_file(local_file_path, bucket_name, s3_file_key)

def main():
    parser = argparse.ArgumentParser(description="Ingest subreddit data into MinIO")
    parser.add_argument(
        "--input-dir",
        default="/data/raw",
        help="Base directory containing subreddit folders",
    )
    parser.add_argument(
        "--output-dir",
        default="/data/processed",
        help="Directory to save processed parquet files",
    )
    parser.add_argument(
        "--s3-bucket",
        default="mh-trends",
        help="S3/MinIO bucket name",
    )
    parser.add_argument(
        "--s3-prefix",
        default="raw",
        help="S3/MinIO key prefix",
    )
    parser.add_argument(
        "--subreddits", 
        nargs="*", 
        help="List of subreddits to process (defaults to all)"
    )
    
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Subreddit Data Ingestion") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Get list of subreddit directories
        if args.subreddits:
            subreddit_dirs = [os.path.join(args.input_dir, s) for s in args.subreddits]
        else:
            subreddit_dirs = [
                os.path.join(args.input_dir, d) for d in os.listdir(args.input_dir)
                if os.path.isdir(os.path.join(args.input_dir, d))
            ]
        
        # Process each subreddit
        for subreddit_dir in subreddit_dirs:
            output_path = process_subreddit(spark, subreddit_dir, args.output_dir)
            
            if output_path:
                # Upload to MinIO
                subreddit_name = os.path.basename(subreddit_dir)
                s3_prefix = f"{args.s3_prefix}/{subreddit_name}"
                upload_to_minio(output_path, args.s3_bucket, s3_prefix)
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 