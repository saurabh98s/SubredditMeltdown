#!/usr/bin/env python3
import argparse
import os
import boto3
import json
import logging
from datetime import datetime

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pyspark.ml.feature import Tokenizer, StopWordsRemover
from pyspark.sql.types import FloatType, StringType, StructType, StructField, ArrayType
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_format, avg, count, sum, from_unixtime, explode, udf, when, lower, lit, concat, split, length, desc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def init_s3_client(s3_endpoint, s3_access_key, s3_secret_key):
    """Initialize and test S3 client connection"""
    logger.info(f"Initializing S3 client with endpoint: {s3_endpoint}")
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            region_name="us-east-1",
        )
        # Test connection
        s3_client.list_buckets()
        logger.info("Successfully connected to S3")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to connect to S3: {str(e)}")
        return None

def test_s3_connection(s3_client, bucket_name, key_prefix):
    """Test S3 connection and create required buckets/prefixes"""
    try:
        # Check if bucket exists, create if not
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} exists")
        except:
            logger.info(f"Creating bucket {bucket_name}")
            s3_client.create_bucket(Bucket=bucket_name)
            
        # Create required prefixes (by uploading empty objects)
        required_prefixes = [
            f"{key_prefix}/submissions_sentiment",
            f"{key_prefix}/comments_sentiment",
            f"{key_prefix}/word_analysis"
        ]
        
        for prefix in required_prefixes:
            marker_key = f"{prefix}/.marker"
            try:
                s3_client.head_object(Bucket=bucket_name, Key=marker_key)
                logger.info(f"Prefix {prefix} exists")
            except:
                logger.info(f"Creating prefix {prefix}")
                s3_client.put_object(Bucket=bucket_name, Key=marker_key, Body=b"")
                
        return True
    except Exception as e:
        logger.error(f"Error testing S3 connection: {str(e)}")
        return False

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

def upload_dataframe_as_json(s3_client, df, s3_bucket, s3_key):
    """Upload a DataFrame as JSON to S3"""
    logger.info(f"Uploading DataFrame as JSON to s3://{s3_bucket}/{s3_key}")
    
    try:
        # Convert to list of dicts for JSON serialization
        data_list = df.toPandas().to_dict(orient="records")
        
        # Write to JSON
        json_data = json.dumps(data_list)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=json_data
        )
        logger.info(f"Successfully uploaded DataFrame to s3://{s3_bucket}/{s3_key}")
        return True
    except Exception as e:
        logger.error(f"Error uploading DataFrame to s3://{s3_bucket}/{s3_key}: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        return False

def test_vader_sentiment():
    """Test VADER sentiment on some sample texts"""
    analyzer = SentimentIntensityAnalyzer()
    
    test_texts = [
        "I love this, it's amazing!",
        "This is terrible, I hate it.",
        "Just a neutral statement about nothing.",
        "I'm feeling happy today and everything is going well.",
        "I'm really angry and frustrated with this situation."
    ]
    
    logger.info("Testing VADER sentiment analysis:")
    for text in test_texts:
        scores = analyzer.polarity_scores(text)
        sentiment = "positive" if scores['compound'] > 0.05 else "negative" if scores['compound'] < -0.05 else "neutral"
        logger.info(f"Text: \"{text}\"")
        logger.info(f"  Scores: {scores}")
        logger.info(f"  Sentiment: {sentiment}")
        logger.info("---")

def get_sentiment(text):
    """Get full sentiment scores (negative, neutral, positive, compound)"""
    analyzer = SentimentIntensityAnalyzer()
    if text and isinstance(text, str) and text.strip() not in ["", "[deleted]", "[removed]"]:
        scores = analyzer.polarity_scores(text)
        return (scores['neg'], scores['neu'], scores['pos'], scores['compound'])
    else:
        return (0.0, 0.0, 0.0, 0.0)

def categorize_sentiment(compound):
    """Categorize sentiment based on compound score"""
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"
    
def get_compound_sentiment(text):
    """Calculate VADER sentiment score for a text string"""
    if not text or not isinstance(text, str):
        logger.debug(f"Empty or non-string text: {text}")
        return 0.0
    
    # Clean up text
    clean_text = text.strip()
    if not clean_text or clean_text in ["[deleted]", "[removed]"]:
        logger.debug(f"Cleaned text is empty or deleted/removed: {clean_text}")
        return 0.0
        
    # Create analyzer inside the function - important for UDF serialization
    analyzer = SentimentIntensityAnalyzer()
    
    try:
        scores = analyzer.polarity_scores(clean_text)
        # Debug information
        if abs(scores['compound']) > 0.5:
            logger.debug(f"Strong sentiment found: {clean_text[:100]}... -> {scores}")
        return scores['compound']
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        return 0.0

def analyze_word_frequency(spark, df, output_path, s3_client=None, s3_bucket=None, s3_key_prefix=None, subreddit=None):
    """Analyze word frequency and sentiment by word"""
    logger.info(f"Analyzing word frequency for {'subreddit '+subreddit if subreddit else 'data'}")
    
    try:
        # Extract words from text content
        word_frequency_df = df.select(
            explode(split(lower(col("text_content")), "\\s+")).alias("word")
        ).filter(length("word") > 3)  # Filter out short words
        
        word_counts = word_frequency_df.groupBy("word").count().orderBy(desc("count"))
        
        # Save word counts
        subreddit_suffix = f"_{subreddit}" if subreddit else ""
        word_counts_output = os.path.join(output_path, f"word_counts{subreddit_suffix}")
        logger.info(f"Writing word counts to {word_counts_output}")
        os.makedirs(word_counts_output, exist_ok=True)
        word_counts.limit(1000).write.mode("overwrite").parquet(word_counts_output)
        
        # Analyze sentiment by word
        word_sentiment_df = df.select(
            explode(split(lower(col("text_content")), "\\s+")).alias("word"),
            "sentiment_score"
        ).filter(length("word") > 3)  # Filter out short words
        
        word_sentiment = word_sentiment_df.groupBy("word").agg(
            avg("sentiment_score").alias("avg_sentiment"),
            count("word").alias("count")
        ).filter(col("count") > 5)  # Only words that appear at least 5 times
        
        # Save positive and negative words
        pos_words_output = os.path.join(output_path, f"positive_words{subreddit_suffix}")
        neg_words_output = os.path.join(output_path, f"negative_words{subreddit_suffix}")
        
        # Get most common positive words
        pos_words = word_sentiment.filter(col("avg_sentiment") > 0.0).orderBy(desc("count"))
        logger.info(f"Writing positive words to {pos_words_output}")
        os.makedirs(pos_words_output, exist_ok=True)
        pos_words.limit(1000).write.mode("overwrite").parquet(pos_words_output)
        
        # Get most common negative words
        neg_words = word_sentiment.filter(col("avg_sentiment") < 0.0).orderBy(desc("count"))
        logger.info(f"Writing negative words to {neg_words_output}")
        os.makedirs(neg_words_output, exist_ok=True)
        neg_words.limit(1000).write.mode("overwrite").parquet(neg_words_output)
        
        # Upload to S3 if configured
        if s3_client and s3_bucket and s3_key_prefix:
            word_analysis_s3_key = f"{s3_key_prefix}/word_analysis"
            
            # Upload word counts
            upload_folder_to_s3(
                s3_client, 
                word_counts_output, 
                s3_bucket, 
                f"{word_analysis_s3_key}/word_counts{subreddit_suffix}"
            )
            
            # Upload positive words
            upload_folder_to_s3(
                s3_client, 
                pos_words_output, 
                s3_bucket, 
                f"{word_analysis_s3_key}/positive_words{subreddit_suffix}"
            )
            
            # Upload negative words
            upload_folder_to_s3(
                s3_client, 
                neg_words_output, 
                s3_bucket, 
                f"{word_analysis_s3_key}/negative_words{subreddit_suffix}"
            )
        
        # Show example results
        logger.info("Most common words:")
        word_counts.limit(20).show()
        
        logger.info("Most common positive words:")
        pos_words.limit(20).show()
        
        logger.info("Most common negative words:")
        neg_words.limit(20).show()
        
        logger.info("Words with highest positive sentiment:")
        word_sentiment.filter(col("count") > 10).orderBy(col("avg_sentiment").desc()).limit(20).show()
        
        logger.info("Words with highest negative sentiment:")
        word_sentiment.filter(col("count") > 10).orderBy(col("avg_sentiment").asc()).limit(20).show()
        
        return True
    except Exception as e:
        logger.error(f"Error analyzing word frequency: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        return False

def calculate_daily_sentiment(spark, input_path, output_path, content_type, s3_client=None, s3_bucket=None, s3_key_prefix=None):
    """Calculate daily average sentiment per subreddit"""
    logger.info(f"Processing sentiment for {content_type} from {input_path}")

    # Read parquet files
    try:
        df = spark.read.parquet(input_path)
        logger.info(f"Successfully loaded {df.count()} records from {input_path}")
        
        # Print schema to debug
        logger.info("Schema of the input data:")
        df.printSchema()
        
        # Check if necessary columns exist
        if content_type == "submissions":
            required_cols = ["title", "selftext", "created_utc"]
        else:  # comments
            required_cols = ["body", "created_utc"]
            
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return None

        # Create text content with improved handling
        if content_type == "submissions":
            # Check if columns exist
            df = df.withColumn("title_safe", 
                     when(col("title").isNull(), "").otherwise(col("title")))
            df = df.withColumn("selftext_safe", 
                     when((col("selftext").isNull()) | 
                         (col("selftext") == "[deleted]") | 
                         (col("selftext") == "[removed]"),
                         "").otherwise(col("selftext")))
            df = df.withColumn("text_content", 
                     when(length(col("selftext_safe")) > 0,
                          concat(col("title_safe"), lit(" "), col("selftext_safe")))
                     .otherwise(col("title_safe")))
        else:  # comments
            # Check if column exists
            if "body" not in df.columns:
                logger.error("Missing required column: body")
                return None
                
            df = df.withColumn("text_content", 
                     when(col("body").isNull(), "").otherwise(col("body")))
        
        # Sample some raw text to check
        logger.info("Sample text content after extraction:")
        df.select("text_content").limit(5).show(truncate=False)
        
        # Run test sentiment analysis
        test_vader_sentiment()
        
        # Calculate sentiment scores with UDF
        get_compound_sentiment_udf = udf(get_compound_sentiment, FloatType())
        df = df.withColumn("sentiment_score", get_compound_sentiment_udf(col("text_content")))
        
        # Check for zero sentiment scores
        zero_count = df.filter(col("sentiment_score") == 0.0).count()
        total_count = df.count()
        logger.info(f"Records with zero sentiment: {zero_count} ({zero_count/total_count*100:.2f}%)")
        
        # Show records with non-zero sentiment to confirm it's working
        logger.info("Sample of records with non-zero sentiment:")
        df.filter(col("sentiment_score") != 0.0).select("text_content", "sentiment_score").limit(5).show(truncate=False)
        
        # Show most positive texts
        logger.info("Most positive texts:")
        df.orderBy(col("sentiment_score").desc()).select("text_content", "sentiment_score").limit(3).show(truncate=False)
        
        # Show most negative texts
        logger.info("Most negative texts:")
        df.orderBy(col("sentiment_score").asc()).select("text_content", "sentiment_score").limit(3).show(truncate=False)
        
        # Calculate daily sentiment
        logger.info("Calculating daily sentiment:")
        subreddit = os.path.basename(input_path)
        
        daily_df = df.withColumn(
            "date",
            date_format(from_unixtime(col("created_utc")), "yyyy-MM-dd")
        ).groupBy("date").agg(
            avg("sentiment_score").alias("avg_sentiment"),
            count("*").alias("post_count")
        ).orderBy(col("post_count").desc())
        
        # Add subreddit column
        daily_df = daily_df.withColumn("subreddit", lit(subreddit))
        
        # Create output directory
        sentiment_output = os.path.join(output_path, f"{content_type}_sentiment")
        subreddit_output = os.path.join(sentiment_output, subreddit)
        logger.info(f"Writing sentiment results for {subreddit} to {subreddit_output}")
        os.makedirs(sentiment_output, exist_ok=True)
        
        # Write to parquet
        daily_df.write.mode("overwrite").parquet(subreddit_output)
        
        # Create word analysis output directory
        word_analysis_output = os.path.join(output_path, "word_analysis")
        os.makedirs(word_analysis_output, exist_ok=True)
        
        # Analyze word frequency
        analyze_word_frequency(
            spark, 
            df, 
            word_analysis_output, 
            s3_client=s3_client, 
            s3_bucket=s3_bucket, 
            s3_key_prefix=s3_key_prefix,
            subreddit=subreddit
        )
        
        # Upload to S3 if configured
        if s3_client and s3_bucket and s3_key_prefix:
            s3_sentiment_path = f"{s3_key_prefix}/{content_type}_sentiment/{subreddit}"
            upload_count = upload_folder_to_s3(
                s3_client, 
                subreddit_output, 
                s3_bucket, 
                s3_sentiment_path
            )
            logger.info(f"Uploaded {upload_count} files to S3 path: {s3_sentiment_path}")
        
        return daily_df
        
    except Exception as e:
        logger.error(f"Error processing sentiment for {input_path}: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        return None

def main():
    parser = argparse.ArgumentParser(description="Calculate daily sentiment from Reddit data")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing processed Reddit data files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save sentiment analysis output",
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
        default="mh-trending-subreddits",
        help="S3 bucket for storing processed data",
    )
    parser.add_argument(
        "--s3-key-prefix",
        default="analytics",
        help="S3 key prefix for storing processed data",
    )
    args = parser.parse_args()

    # Parse environment variables for S3 access
    s3_endpoint = os.environ.get("S3_ENDPOINT", "http://minio:9000")
    s3_access_key = os.environ.get("S3_ACCESS_KEY", "minioadmin")
    s3_secret_key = os.environ.get("S3_SECRET_KEY", "minioadmin")
    
    # Initialize S3 client if needed
    s3_client = None
    if args.upload_to_s3:
        s3_client = init_s3_client(s3_endpoint, s3_access_key, s3_secret_key)
        if s3_client:
            test_s3_connection(s3_client, args.s3_bucket, args.s3_key_prefix)
        else:
            logger.warning("Failed to initialize S3 client, uploads will be skipped")

    # Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Sentiment Analysis") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", s3_access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", s3_secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    # Test the sentiment analyzer to ensure it's working
    logger.info("Testing sentiment analyzer...")
    test_vader_sentiment()
    
    # Register the sentiment UDF for better distributed performance
    get_compound_sentiment_udf = udf(get_compound_sentiment, FloatType())
    spark.udf.register("get_compound_sentiment", get_compound_sentiment, FloatType())
    
    # Process sentiment for each content type
    if args.content_type in ["submissions", "all"]:
        submissions_input = os.path.join(args.input_dir, "submissions")
        submissions_output = os.path.join(args.output_dir)
        
        # Check if input directory exists
        if os.path.exists(submissions_input):
            # Process specific subreddits if requested
            if args.subreddits:
                for subreddit in args.subreddits:
                    subreddit_path = os.path.join(submissions_input, subreddit)
                    if os.path.exists(subreddit_path):
                        calculate_daily_sentiment(
                            spark, 
                            subreddit_path, 
                            submissions_output, 
                            "submissions",
                            s3_client=s3_client if args.upload_to_s3 else None,
                            s3_bucket=args.s3_bucket if args.upload_to_s3 else None,
                            s3_key_prefix=args.s3_key_prefix if args.upload_to_s3 else None
                        )
                    else:
                        logger.warning(f"Subreddit directory not found: {subreddit_path}")
            else:
                # Process all subreddits
                subreddit_dirs = []
                for item in os.listdir(submissions_input):
                    item_path = os.path.join(submissions_input, item)
                    if os.path.isdir(item_path):
                        subreddit_dirs.append(item)
                
                logger.info(f"Found subreddits: {subreddit_dirs}")
                for subreddit in subreddit_dirs:
                    subreddit_path = os.path.join(submissions_input, subreddit)
                    calculate_daily_sentiment(
                        spark, 
                        subreddit_path, 
                        submissions_output, 
                        "submissions",
                        s3_client=s3_client if args.upload_to_s3 else None,
                        s3_bucket=args.s3_bucket if args.upload_to_s3 else None,
                        s3_key_prefix=args.s3_key_prefix if args.upload_to_s3 else None
                    )
        else:
            logger.warning(f"Input directory not found: {submissions_input}")
    
    if args.content_type in ["comments", "all"]:
        comments_input = os.path.join(args.input_dir, "comments")
        comments_output = os.path.join(args.output_dir)
        
        # Check if input directory exists
        if os.path.exists(comments_input):
            # Process specific subreddits if requested
            if args.subreddits:
                for subreddit in args.subreddits:
                    subreddit_path = os.path.join(comments_input, subreddit)
                    if os.path.exists(subreddit_path):
                        calculate_daily_sentiment(
                            spark, 
                            subreddit_path, 
                            comments_output, 
                            "comments",
                            s3_client=s3_client if args.upload_to_s3 else None,
                            s3_bucket=args.s3_bucket if args.upload_to_s3 else None,
                            s3_key_prefix=args.s3_key_prefix if args.upload_to_s3 else None
                        )
                    else:
                        logger.warning(f"Subreddit directory not found: {subreddit_path}")
            else:
                # Process all subreddits
                subreddit_dirs = []
                for item in os.listdir(comments_input):
                    item_path = os.path.join(comments_input, item)
                    if os.path.isdir(item_path):
                        subreddit_dirs.append(item)
                
                logger.info(f"Found subreddits: {subreddit_dirs}")
                for subreddit in subreddit_dirs:
                    subreddit_path = os.path.join(comments_input, subreddit)
                    calculate_daily_sentiment(
                        spark, 
                        subreddit_path, 
                        comments_output, 
                        "comments",
                        s3_client=s3_client if args.upload_to_s3 else None,
                        s3_bucket=args.s3_bucket if args.upload_to_s3 else None,
                        s3_key_prefix=args.s3_key_prefix if args.upload_to_s3 else None
                    )
        else:
            logger.warning(f"Input directory not found: {comments_input}")
    
    logger.info("Sentiment analysis completed")
    spark.stop()

if __name__ == "__main__":
    main() 