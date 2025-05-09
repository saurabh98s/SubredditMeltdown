#!/usr/bin/env python3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, when, lit
from pyspark.sql.types import StringType, StructType, StructField
import argparse
import os
import glob
from datetime import datetime
import boto3
import langdetect
import logging

#Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define schema for Reddit submissions (posts)
submission_schema = StructType([
    StructField("id", StringType(), True),
    StructField("title", StringType(), True),
    StructField("author", StringType(), True),
    StructField("subreddit", StringType(), True),
    StructField("selftext", StringType(), True),
    StructField("created_utc", StringType(), True),
    StructField("score", StringType(), True),
    StructField("num_comments", StringType(), True),
])

#Define schema for Reddit comments
comment_schema = StructType([
 StructField("id", StringType(), True),
    StructField("title", StringType(), True),
    StructField("author", StringType(), True),
    StructField("subreddit", StringType(), True),
    StructField("selftext", StringType(), True),
    StructField("created_utc", StringType(), True),
    StructField("score", StringType(), True),
    StructField("num_comments", StringType(), True),
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

def find_jsonl_files(input_dir, file_pattern):
    """Find all JSONL files matching the pattern in the input directory and its subdirectories"""
    result = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.jsonl') and file_pattern in file:
                result.append(os.path.join(root, file))
    return result

def process_submissions(spark, input_dir, output_path):
    """Process Reddit submissions from JSONL files"""
    logger.info(f"Looking for post files in {input_dir}")
    
    # Find all post JSONL files
    post_files = find_jsonl_files(input_dir, "posts")
    if not post_files:
        logger.warning(f"No post files found in {input_dir}")
        return
    
    logger.info(f"Found {len(post_files)} post files to process")
    
    # Read and process each file, then union them
    all_submissions = None
    
    for file_path in post_files:
        logger.info(f"Processing posts from {file_path}")
        subreddit = file_path.split("/")[-3] if "/raw/" in file_path else "unknown"
        
        # Read submissions
        df = spark.read.json(file_path, schema=submission_schema)
        
        # If subreddit column is empty, add it from the folder name
        if "subreddit" in df.columns:
            df = df.withColumn(
                "subreddit", 
                when(col("subreddit").isNull(), lit(subreddit)).otherwise(col("subreddit"))
            )
        else:
            df = df.withColumn("subreddit", lit(subreddit))
        
        # Union with previous dataframes
        if all_submissions is None:
            all_submissions = df
        else:
            all_submissions = all_submissions.union(df)
    
    if all_submissions is None:
        logger.warning("No submission data found to process")
        return
    
    # Clean and filter submissions
    cleaned_submissions = all_submissions.filter(
        # Filter out deleted/removed content
        (col("selftext").isNotNull()) &
        (col("selftext") != "[deleted]") & 
        (col("selftext") != "[removed]") &
        (col("author").isNotNull()) &
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
    
    count = result.count()
    logger.info(f"Writing {count} cleaned submissions to {output_path}")
    result.write.mode("overwrite").parquet(output_path)
    return count

def process_comments(spark, input_dir, output_path):
    """Process Reddit comments from JSONL files"""
    logger.info(f"Looking for comment files in {input_dir}")
    
    # Find all comment JSONL files
    comment_files = find_jsonl_files(input_dir, "comments")
    if not comment_files:
        logger.warning(f"No comment files found in {input_dir}")
        return
    
    logger.info(f"Found {len(comment_files)} comment files to process")
    
    # Read and process each file, then union them
    all_comments = None
    
    for file_path in comment_files:
        logger.info(f"Processing comments from {file_path}")
        subreddit = file_path.split("/")[-3] if "/raw/" in file_path else "unknown"
        
        # Read comments
        df = spark.read.json(file_path, schema=comment_schema)
        
        # If subreddit column is empty, add it from the folder name
        if "subreddit" in df.columns:
            df = df.withColumn(
                "subreddit", 
                when(col("subreddit").isNull(), lit(subreddit)).otherwise(col("subreddit"))
            )
        else:
            df = df.withColumn("subreddit", lit(subreddit))
        
        # Union with previous dataframes
        if all_comments is None:
            all_comments = df
        else:
            all_comments = all_comments.union(df)
    
    if all_comments is None:
        logger.warning("No comment data found to process")
        return
    
    #Clean and filter comments
    cleaned_comments = all_comments.filter(
        # Filter out deleted/removed content
        (col("body").isNotNull()) &
        (col("body") != "[deleted]") & 
        (col("body") != "[removed]") &
        (col("author").isNotNull()) &
        (col("author") != "[deleted]") &
        (col("author") != "AutoModerator")
    )
    
    # Detect language
    cleaned_comments = cleaned_comments.withColumn(
        "language", detect_language_udf(col("body"))
    )
    
    #Keep only English content
    english_comments = cleaned_comments.filter(col("language") == "en")
    
    #Select relevant columns and write to parquet
    result = english_comments.select(
        "id", "body", "author", "subreddit", "created_utc", "score", "parent_id"
    )
    
    count = result.count()
    logger.info(f"Writing {count} cleaned comments to {output_path}")
    result.write.mode("overwrite").parquet(output_path)
    return count

def test_s3_connection(s3_endpoint, s3_access_key, s3_secret_key, bucket_name, required_prefixes=None):
    """Test connection to S3 and verify/create required buckets and prefixes"""
    logger.info(f"Testing connection to S3 at {s3_endpoint}")
    logger.info(f"S3 Access Key: {s3_access_key}")
    logger.info(f"S3 Secret Key present: {'Yes' if s3_secret_key else 'No'}")

    try:
        #Configure S3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            region_name="us-east-1",
        )
        
        #Test connection by listing buckets
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        logger.info(f"Available buckets: {buckets}")
        
        #Check if our bucket exists
        bucket_exists = bucket_name in buckets
        if not bucket_exists:
            logger.info(f"Bucket '{bucket_name}' doesn't exist, creating it")
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created bucket '{bucket_name}'")
        else:
            logger.info(f"Bucket '{bucket_name}' already exists")
        
        #Create required prefixes (folders)
        if required_prefixes:
            for prefix in required_prefixes:
                prefix_path = f"{prefix}/"
                logger.info(f"Ensuring prefix '{prefix_path}' exists in bucket '{bucket_name}'")
                s3_client.put_object(Bucket=bucket_name, Key=prefix_path)
        
        return True, s3_client
    except Exception as e:
        logger.error(f"S3 connection error: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        return False, None

def upload_folder_to_s3(s3_client, local_path, s3_bucket, s3_key):
    """Upload a folder to S3"""
    logger.info(f"Uploading folder {local_path} to s3://{s3_bucket}/{s3_key}")
    file_count = 0
    
    try:
        for root, _, files in os.walk(local_path):
            for file in files:
                if file.endswith('.parquet') or file.endswith('_SUCCESS'):
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, local_path)
                    s3_file_key = os.path.join(s3_key, relative_path)
                    
                    logger.info(f"Uploading {local_file_path} to s3://{s3_bucket}/{s3_file_key}")
                    try:
                        s3_client.upload_file(local_file_path, s3_bucket, s3_file_key)
                        file_count += 1
                    except Exception as upload_error:
                        logger.error(f"Failed to upload {local_file_path}: {str(upload_error)}")
        
        logger.info(f"Uploaded {file_count} files from {local_path} to s3://{s3_bucket}/{s3_key}")
        return file_count
    except Exception as e:
        logger.error(f"Error uploading folder {local_path}: {str(e)}")
        return 0

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
        "--subreddits",
        nargs="+",
        help="Specific subreddits to process (default: all)",
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
    
    # Get S3 environment variables
    s3_endpoint = os.environ.get("S3_ENDPOINT", "http://minio:9000")
    s3_access_key = os.environ.get("S3_ACCESS_KEY", "minioadmin")
    s3_secret_key = os.environ.get("S3_SECRET_KEY", "minioadmin")
    
    # Test S3 connection if uploads are requested
    s3_client = None
    if args.upload_to_s3:
        logger.info("Testing S3 connection before starting data processing")
        required_prefixes = [
            f"{args.s3_key_prefix}/submissions",
            f"{args.s3_key_prefix}/comments"
        ]
        connection_ok, s3_client = test_s3_connection(
            s3_endpoint, s3_access_key, s3_secret_key, 
            args.s3_bucket, required_prefixes
        )
        
        if not connection_ok:
            logger.error("Failed to connect to S3. Processing will continue but data won't be uploaded.")
            args.upload_to_s3 = False
    
    #Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Data Cleaning") \
        .config("spark.driver.memory", "1g") \
        .config("spark.executor.memory", "1g") \
        .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", s3_access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", s3_secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    #Create output directories
    submissions_output = os.path.join(args.output_dir, "submissions")
    comments_output = os.path.join(args.output_dir, "comments")
    os.makedirs(submissions_output, exist_ok=True)
    os.makedirs(comments_output, exist_ok=True)
    
    input_dir = args.input_dir
    
    #Filter for specific subreddits if provided
    subreddit_dirs = []
    if args.subreddits:
        for subreddit in args.subreddits:
            subreddit_path = os.path.join(input_dir, subreddit.lower())
            if os.path.exists(subreddit_path):
                subreddit_dirs.append(subreddit_path)
            else:
                logger.warning(f"Subreddit directory not found: {subreddit_path}")
    else:
        #Use all subreddit directories
        subreddit_dirs = [os.path.join(input_dir, d) for d in os.listdir(input_dir) 
                          if os.path.isdir(os.path.join(input_dir, d)) and d != ".ipynb_checkpoints"]
    
    if not subreddit_dirs:
        logger.error(f"No valid subreddit directories found in {input_dir}")
        return
    
    logger.info(f"Processing subreddits: {', '.join([os.path.basename(d) for d in subreddit_dirs])}")
    
    try:
        submissions_count = 0
        comments_count = 0
        
        #Process each subreddit directory
        for subreddit_dir in subreddit_dirs:
            subreddit_name = os.path.basename(subreddit_dir)
            logger.info(f"Processing subreddit: {subreddit_name}")
            
            subreddit_submissions_output = os.path.join(submissions_output, subreddit_name)
            subreddit_comments_output = os.path.join(comments_output, subreddit_name)
            
            #Process submissions
            if args.content_type in ["submissions", "all"]:
                count = process_submissions(spark, subreddit_dir, subreddit_submissions_output)
                if count:
                    submissions_count += count
                    
                    # Upload this subreddit's submissions to S3 immediately
                    if args.upload_to_s3 and s3_client and count > 0:
                        s3_key = f"{args.s3_key_prefix}/submissions/{subreddit_name}"
                        upload_folder_to_s3(s3_client, subreddit_submissions_output, args.s3_bucket, s3_key)
            
            # Process comments
            if args.content_type in ["comments", "all"]:
                count = process_comments(spark, subreddit_dir, subreddit_comments_output)
                if count:
                    comments_count += count
                    
                    # Upload this subreddit's comments to S3 immediately
                    if args.upload_to_s3 and s3_client and count > 0:
                        s3_key = f"{args.s3_key_prefix}/comments/{subreddit_name}"
                        upload_folder_to_s3(s3_client, subreddit_comments_output, args.s3_bucket, s3_key)
        
        logger.info(f"Total processed: {submissions_count} submissions, {comments_count} comments")
    
    finally:
        # Stop Spark session
        spark.stop()

if __name__ == "__main__":
    main() 