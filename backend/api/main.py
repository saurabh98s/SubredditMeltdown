from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import boto3
import tempfile
import pandas as pd
import pyarrow.parquet as pq
from io import BytesIO
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reddit Meltdown Analysis API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# S3/MinIO configuration
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
        verify=False,
    )

s3_client = get_s3_client()
bucket_name = os.environ.get("S3_BUCKET", "mh-trending-subreddits")

# Model definitions
class SentimentData(BaseModel):
    subreddit: str
    date: str
    avg_sentiment: float
    post_count: int

class EventData(BaseModel):
    date: str
    event: str
    category: str

class KeywordData(BaseModel):
    keyword: str
    weight: float
    timeframe: str
    subreddit: str

@app.get("/")
async def root():
    return {"message": "Reddit Meltdown Analysis API"}

@app.get("/subreddits", response_model=List[str])
async def get_subreddits():
    """Get list of available subreddits"""
    try:
        # First try to get from submissions_sentiment directory
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix="analytics/submissions_sentiment/",
                Delimiter="/"
            )
            
            subreddits = []
            if 'CommonPrefixes' in response:
                for obj in response['CommonPrefixes']:
                    # Extract subreddit name from prefix
                    subreddit = obj['Prefix'].split('/')[-2]
                    subreddits.append(subreddit)
            
            if subreddits:
                return subreddits
                
        except Exception as e:
            logger.warning(f"Could not list submissions_sentiment directory: {str(e)}")

        # Fallback to listing directories
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix="analytics/",
                Delimiter="/"
            )
            
            subreddits = []
            if 'CommonPrefixes' in response:
                for obj in response['CommonPrefixes']:
                    # Extract directory name from prefix
                    dirname = obj['Prefix'].split('/')[-2]
                    if dirname not in ['submissions_sentiment', 'comments_sentiment', 'word_analysis']:
                        subreddits.append(dirname)
            
            return subreddits
        except Exception as e2:
            logger.error(f"Error listing subreddits as fallback: {str(e2)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve subreddit list")
    except Exception as e:
        logger.error(f"Error retrieving subreddits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def read_parquet_from_minio(bucket, prefix):
    """Read parquet files from MinIO into a pandas DataFrame"""
    try:
        # List all parquet files in the directory
        logger.info(f"Listing objects in {bucket}/{prefix}")
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.warning(f"No objects found in {bucket}/{prefix}")
            return pd.DataFrame()
            
        parquet_files = [obj['Key'] for obj in response['Contents'] 
                        if obj['Key'].endswith('.parquet') and not obj['Key'].endswith('_SUCCESS')]
        
        if not parquet_files:
            logger.warning(f"No parquet files found in {bucket}/{prefix}")
            return pd.DataFrame()
            
        logger.info(f"Found {len(parquet_files)} parquet files")
        
        # Download and read each parquet file
        dataframes = []
        for file_key in parquet_files:
            try:
                logger.info(f"Reading {file_key}")
                response = s3_client.get_object(Bucket=bucket, Key=file_key)
                parquet_data = BytesIO(response['Body'].read())
                
                df = pq.read_table(parquet_data).to_pandas()
                logger.info(len(df.columns))
                dataframes.append(df)
            except Exception as e:
                logger.error(f"Error reading parquet file {file_key}: {str(e)}")
                continue
                
        if not dataframes:
            logger.warning("No dataframes could be created from parquet files")
            return pd.DataFrame()
            
        # Combine all dataframes
        combined_df = pd.concat(dataframes, ignore_index=True)
        return combined_df
        
    except Exception as e:
        logger.error(f"Error reading parquet from MinIO: {str(e)}")
        return pd.DataFrame()

@app.get("/sentiment", response_model=List[SentimentData])
async def get_sentiment(
    subreddit: str = Query(..., description="Subreddit name"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    content_type: str = Query("submissions", description="Content type (submissions or comments)")
):
    """Get sentiment data for a specific subreddit and date range"""
    try:
        # Path to sentiment data in MinIO
        s3_path = f"analytics/{content_type}_sentiment/{subreddit}"
        
        logger.info(f"Getting sentiment for {subreddit} from {s3_path}")
        
        # Read parquet data from MinIO
        df = read_parquet_from_minio(bucket_name, s3_path)
        
        if df.empty:
            logger.warning(f"No sentiment data found for subreddit: {subreddit}")
            return []
            
        # Log schema for debugging
        logger.info(f"DataFrame columns: {df.columns.tolist()}")
        logger.info(f"DataFrame sample: {df.head(2).to_dict('records')}")
        
        # Ensure column names match expected format
        df_columns = df.columns.tolist()
        logger.info(len(df_columns))
        
        # Rename columns if needed
        column_mapping = {}
        if 'date' not in df_columns and 'date' in df:
            column_mapping['date'] = 'date'
        if 'avg_sentiment' not in df_columns:
            for col in df_columns:
                if 'sentiment' in col.lower():
                    column_mapping[col] = 'avg_sentiment'
                    break
        if 'post_count' not in df_columns:
            for col in df_columns:
                if 'count' in col.lower():
                    column_mapping[col] = 'post_count'
                    break
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Ensure subreddit column exists
        if 'subreddit' not in df.columns:
            df['subreddit'] = subreddit
            
        # Ensure date column is string format
        df['date'] = df['date'].astype(str)
        
        # Filter by date range
        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        if filtered_df.empty:
            logger.warning(f"No data found in date range {start_date} to {end_date}")
            return []
            
        # Convert to list of dictionaries
        result = filtered_df.to_dict('records')
        
        # Convert to SentimentData objects
        sentiment_data = []
        for item in result:
            try:
                sentiment_data.append(SentimentData(
                    subreddit=item['subreddit'],
                    date=item['date'],
                    avg_sentiment=float(item['avg_sentiment']),
                    post_count=int(item['post_count'])
                ))
            except Exception as e:
                logger.error(f"Error converting item to SentimentData: {str(e)}, item: {item}")
                continue
        
        return sentiment_data
        
    except Exception as e:
        logger.error(f"Error retrieving sentiment data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events", response_model=List[EventData])
async def get_events(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Event category")
):
    """Get major events for a specific date range and optional category"""
    try:
        # Path to events data in MinIO
        s3_path = "analytics/events"
        
        try:
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=s3_path
            )
            data = json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning("No events data found")
                return []
            else:
                raise
        
        # Filter by date range and category if provided
        filtered_data = [
            d for d in data 
            if start_date <= d["date"] <= end_date and
            (category is None or d["category"] == category)
        ]
        
        return filtered_data
    except Exception as e:
        logger.error(f"Error retrieving events data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keywords", response_model=List[KeywordData])
async def get_keywords(
    subreddit: str = Query(..., description="Subreddit name"),
    timeframe: str = Query(..., description="Timeframe (daily, weekly, monthly)")
):
    """Get top keywords for a specific subreddit and timeframe"""
    try:
        # First try to get from word_analysis directory
        s3_path = f"analytics/word_analysis/positive_words_{subreddit}"
        
        # Read parquet data from MinIO
        df = read_parquet_from_minio(bucket_name, s3_path)
        
        if df.empty:
            # Try negative words
            s3_path = f"analytics/word_analysis/negative_words_{subreddit}"
            df = read_parquet_from_minio(bucket_name, s3_path)
            
        if df.empty:
            logger.warning(f"No keyword data found for subreddit: {subreddit}")
            return []
            
        # Log schema for debugging
        logger.info(f"Keywords DataFrame columns: {df.columns.tolist()}")
        
        # Ensure necessary columns exist
        if 'word' not in df.columns or 'avg_sentiment' not in df.columns or 'count' not in df.columns:
            logger.warning(f"Missing required columns in keyword data")
            return []
            
        # Sort by count (descending)
        df = df.sort_values(by='count', ascending=False)
        
        # Take top 50 keywords
        top_df = df
        
        # Convert to the expected format
        keywords = []
        for _, row in top_df.iterrows():
            keywords.append(KeywordData(
                keyword=row['word'],
                weight=float(row['count']),
                timeframe=timeframe,
                subreddit=subreddit
            ))
            
        return keywords
            
    except Exception as e:
        logger.error(f"Error retrieving keyword data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subreddit/stats", response_model=Dict[str, Any])
async def get_subreddit_stats(subreddit: str = Query(..., description="Subreddit name")):
    """Get statistics for a specific subreddit"""
    try:
        # First check if the subreddit exists
        subreddits = await get_subreddits()
        if subreddit not in subreddits:
            raise HTTPException(status_code=404, detail=f"Subreddit '{subreddit}' not found")
        
        # Get sentiment for the last 30 days
        today = datetime.now()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        sentiment_data = await get_sentiment(subreddit, start_date, end_date)
        
        # Get keywords
        keywords_data = await get_keywords(subreddit, "weekly")
        
        # Calculate statistics
        stats = {
            "subreddit": subreddit,
            "post_count": sum(item.post_count for item in sentiment_data) if sentiment_data else 0,
            "sentiment": {
                "current": sentiment_data[-1].avg_sentiment if sentiment_data else 0,
                "trend": "neutral",
                "history": [{"date": item.date, "sentiment_score": item.avg_sentiment} for item in sentiment_data]
            },
            "top_keywords": keywords_data[:10] if keywords_data else []
        }
        
        # Determine sentiment trend
        if sentiment_data and len(sentiment_data) > 1:
            first_half = sentiment_data[:len(sentiment_data)//2]
            second_half = sentiment_data[len(sentiment_data)//2:]
            
            first_avg = sum(item.avg_sentiment for item in first_half) / len(first_half) if first_half else 0
            second_avg = sum(item.avg_sentiment for item in second_half) / len(second_half) if second_half else 0
            
            if second_avg - first_avg > 0.1:
                stats["sentiment"]["trend"] = "positive"
            elif first_avg - second_avg > 0.1:
                stats["sentiment"]["trend"] = "negative"
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving subreddit stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trending", response_model=List[Dict[str, Any]])
async def get_trending_subreddits():
    """Get trending subreddits based on recent activity and sentiment"""
    try:
        # Get list of all subreddits
        subreddits = await get_subreddits()
        
        # For each subreddit, get recent sentiment
        trending = []
        for subreddit in subreddits[:10]:  # Limit to 10 for performance
            try:
                stats = await get_subreddit_stats(subreddit)
                trending.append({
                    "subreddit": subreddit,
                    "sentiment_trend": stats["sentiment"]["trend"],
                    "current_sentiment": stats["sentiment"]["current"],
                    "post_count": stats["post_count"],
                    "top_keywords": [kw.keyword for kw in stats["top_keywords"][:3]] if stats["top_keywords"] else []
                })
            except Exception as e:
                logger.error(f"Error getting stats for {subreddit}: {str(e)}")
                continue
        
        # Sort by current sentiment
        trending.sort(key=lambda x: abs(x["current_sentiment"]), reverse=True)
        
        return trending
    except Exception as e:
        logger.error(f"Error retrieving trending subreddits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 