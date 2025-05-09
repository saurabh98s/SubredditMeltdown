#!/usr/bin/env python3
import argparse
import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, split, lower, count, desc, udf, lit, when, length, date_format, from_unixtime, avg, concat
from pyspark.sql.types import FloatType, StringType, ArrayType, StructType, StructField
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def get_sentiment_score(text):
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

def run_sentiment_analysis(spark, input_file):
    """Run sentiment analysis on the input Parquet file"""
    logger.info(f"Running sentiment analysis on: {input_file}")
    
    # First test VADER sentiment directly
    test_vader_sentiment()
    
    # Load the parquet file
    df = spark.read.parquet(input_file)
    
    # Log the schema to debug column issues
    logger.info("DataFrame schema:")
    df.printSchema()
    
    # Log a few raw records to see what we're working with
    logger.info("Raw data sample:")
    df.select("*").show(5, truncate=False)
    
    # Create a UDF for sentiment analysis
    sentiment_udf = udf(get_sentiment_score, FloatType())
    
    # Get content type from path
    content_type = "submissions" if "submissions" in input_file else "comments"
    
    # For submissions, combine title and selftext
    if content_type == "submissions":
        # Check if columns exist
        required_cols = ["title", "selftext"]
        missing_cols = [col_name for col_name in required_cols if col_name not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return
            
        # Create text_content with improved handling of null values
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
            return
            
        df = df.withColumn("text_content", 
                     when(col("body").isNull(), "").otherwise(col("body")))
    
    # Sample some raw text to check
    logger.info("Sample text content after extraction:")
    df.select("text_content").limit(5).show(truncate=False)
    
    # Calculate sentiment scores
    df = df.withColumn("sentiment_score", sentiment_udf(col("text_content")))
    
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
    
    # Get word frequency counts
    word_frequency_df = df.select(
        explode(split(lower(col("text_content")), "\\s+")).alias("word")
    ).filter(length("word") > 3)  # Filter out short words
    
    word_counts = word_frequency_df.groupBy("word").count().orderBy(col("count").desc())
    
    logger.info("Most common words:")
    word_counts.limit(20).show()
    
    # Analyze sentiment by word
    word_sentiment_df = df.select(
        explode(split(lower(col("text_content")), "\\s+")).alias("word"),
        "sentiment_score"
    ).filter(length("word") > 3)  # Filter out short words
    
    word_sentiment = word_sentiment_df.groupBy("word").agg(
        avg("sentiment_score").alias("avg_sentiment"),
        count("word").alias("count")
    ).filter(col("count") > 5)  # Only words that appear at least 5 times
    
    logger.info("Most common positive words:")
    word_sentiment.filter(col("avg_sentiment") > 0).orderBy(col("count").desc()).limit(20).show()
    
    logger.info("Most common negative words:")
    word_sentiment.filter(col("avg_sentiment") < 0).orderBy(col("count").desc()).limit(20).show()
    
    # Calculate most positive/negative words
    logger.info("Words with highest positive sentiment:")
    word_sentiment.filter(col("count") > 10).orderBy(col("avg_sentiment").desc()).limit(20).show()
    
    logger.info("Words with highest negative sentiment:")
    word_sentiment.filter(col("count") > 10).orderBy(col("avg_sentiment").asc()).limit(20).show()
    
    # Calculate daily sentiment
    logger.info("Daily sentiment:")
    try:
        daily_df = df.withColumn(
            "date",
            date_format(from_unixtime(col("created_utc")), "yyyy-MM-dd")
        ).groupBy("date").agg(
            avg("sentiment_score").alias("avg_sentiment"),
            count("*").alias("post_count")
        ).orderBy(col("post_count").desc())
        
        # Write to parquet
        output_dir = "/data/analytics/submissions_sentiment"
        os.makedirs(output_dir, exist_ok=True)
        subreddit = os.path.basename(input_file)
        subreddit_output = os.path.join(output_dir, subreddit)
        logger.info(f"Writing sentiment results for {subreddit} to {subreddit_output}")
        
        daily_df = daily_df.withColumn("subreddit", lit(subreddit))
        daily_df.write.mode("overwrite").parquet(subreddit_output)
    except Exception as e:
        logger.error(f"Error processing {input_file}: {str(e)}")
        logger.error("Full exception:", exc_info=True)

def main():
    parser = argparse.ArgumentParser(description="Test sentiment analysis")
    parser.add_argument(
        "--input-file",
        required=True,
        help="Parquet file containing Reddit data",
    )
    args = parser.parse_args()

    # Create Spark session
    spark = SparkSession.builder \
        .appName("Reddit Sentiment Analysis Test") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .getOrCreate()
    
    # Run sentiment analysis
    run_sentiment_analysis(spark, args.input_file)
    
if __name__ == "__main__":
    main() 