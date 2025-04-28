#!/usr/bin/env python3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, when, explode, from_json, lit
from pyspark.sql.types import StringType, ArrayType, StructType, StructField, BooleanType
import argparse
import os
from datetime import datetime
import boto3
import langdetect
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define schema for Reddit submissions
submission_schema = StructType([
    StructField("id", StringType(), True),
    StructField("title", StringType(), True),
    StructField("author", StringType(), True),
    StructField("subreddit", StringType(), True),
    StructField("selftext", StringType(), True),
    StructField("created_utc", StringType(), True),
    StructField("score", StringType(), True),
    StructField("num_comments", StringType(), True),
    # Add other fields as needed
])

# Define schema for Reddit comments
comment_schema = StructType([
    StructField("id", StringType(), True),
    StructField("body", StringType(), True),
    StructField("author", StringType(), True),
    StructField("subreddit", StringType(), True),
    StructField("created_utc", StringType(), True),
    StructField("score", StringType(), True),
    StructField("parent_id", StringType(), True),
    # Add other fields as needed
])

# Function to detect language
def detect_language(text):
    if text is None or text == "" or text == "[deleted]" or text == "[removed]":
        return None
    try:
        return langdetect.detect(text)
    except:
        return None

# Register UDF
detect_language_udf = udf(detect_language, StringType())

def process_submissions(spark, input_path, output_path):
    """Process Reddit submissions"""
    logger.info(f"Processing submissions from {input_path}")
    
    # Read submissions
    submissions_df = spark.read.json(input_path, schema=submission_schema)
    
    # Clean and filter submissions
    cleaned_submissions = submissions_df.filter(
        # Filter out deleted/removed content
        (col("selftext") != "[deleted]") & 
        (col("selftext") != "[removed]") &
        (col("author") != "[deleted]") &
        (col("author") != "AutoModerator")
    )
    
    # Detect language
    cleaned_submissions = cleaned_submissions.withColumn(
        "language", detect_language_udf(col("selftext"))
    )
    
    # Keep only English content
    english_submissions = cleaned_submissions.filter(col("language") == "en")
    
    # Select relevant columns and write to parquet
    result = english_submissions.select(
        "id", "title", "author", "subreddit", "selftext", "created_utc", "score", "num_comments"
    )
    
    logger.info(f"Writing {result.count()} cleaned submissions to {output_path}")
    result.write.mode("overwrite").parquet(output_path)

def process_comments(spark, input_path, output_path):
    """Process Reddit comments"""
    logger.info(f"Processing comments from {input_path}")
    
    # Read comments
    comments_df = spark.read.json(input_path, schema=comment_schema)
    
    # Clean and filter comments
    cleaned_comments = comments_df.filter(
        # Filter out deleted/removed content
        (col("body") != "[deleted]") & 
        (col("body") != "[removed]") &
        (col("author") != "[deleted]") &
        (col("author") != "AutoModerator")
    )
    
    # Detect language
    cleaned_comments = cleaned_comments.withColumn(
        "language", detect_language_udf(col("body"))
    )
    
    # Keep only English content
    english_comments = cleaned_comments.filter(col("language") == "en")
    
    # Select relevant columns and write to parquet
    result = english_comments.select(
        "id", "body", "author", "subreddit", "created_utc", "score", "parent_id"
    )
    
    logger.info(f"Writing {result.count()} cleaned comments to {output_path}")
    result.write.mode("overwrite").parquet(output_path)

def upload_to_s3(local_path, s3_bucket, s3_key):
    """Upload processed data to S3"""
    # Configure S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    
    # Upload files
    for root, _, files in os.walk(local_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_file_path, local_path)
            s3_file_key = os.path.join(s3_key, relative_path)
            
            logger.info(f"Uploading {local_file_path} to s3://{s3_bucket}/{s3_file_key}")
            s3_client.upload_file(local_file_path, s3_bucket, s3_file_key)

def main():
    parser = argparse.ArgumentParser(description="Clean and preprocess Reddit data")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing raw Reddit data files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save processed Parquet files",
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
        default="cleaned",
        help="S3 key prefix (default: cleaned)",
    )
    
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Data Cleaning") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()
    
    # Create output directories
    submissions_output = os.path.join(args.output_dir, "submissions")
    comments_output = os.path.join(args.output_dir, "comments")
    os.makedirs(submissions_output, exist_ok=True)
    os.makedirs(comments_output, exist_ok=True)
    
    try:
        # Process submissions
        if args.content_type in ["submissions", "all"]:
            submissions_input = os.path.join(args.input_dir, "RS_*.zst")
            process_submissions(spark, submissions_input, submissions_output)
        
        # Process comments
        if args.content_type in ["comments", "all"]:
            comments_input = os.path.join(args.input_dir, "RC_*.zst")
            process_comments(spark, comments_input, comments_output)
        
        # Upload to S3 if requested
        if args.upload_to_s3:
            if args.content_type in ["submissions", "all"]:
                upload_to_s3(
                    submissions_output,
                    args.s3_bucket,
                    f"{args.s3_key_prefix}/submissions"
                )
            
            if args.content_type in ["comments", "all"]:
                upload_to_s3(
                    comments_output,
                    args.s3_bucket,
                    f"{args.s3_key_prefix}/comments"
                )
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 