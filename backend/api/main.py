from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import boto3
from datetime import datetime, timedelta

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
s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ.get("S3_ENDPOINT", "http://minio:9000"),
    aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
    region_name="us-east-1",
)
bucket_name = os.environ.get("S3_BUCKET", "mh-trends")

# Model definitions
class SentimentData(BaseModel):
    subreddit: str
    date: str
    sentiment_score: float

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

@app.get("/sentiment", response_model=List[SentimentData])
async def get_sentiment(subreddit: str, start_date: str, end_date: str):
    """Get sentiment data for a specific subreddit and date range"""
    try:
        # Path to sentiment data in S3
        s3_path = f"analytics/sentiment_daily/{subreddit}"
        
        # In a real implementation, you would query and filter the data
        # This is a placeholder for demonstration
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=s3_path
        )
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Filter by date range
        filtered_data = [
            d for d in data 
            if start_date <= d["date"] <= end_date
        ]
        
        return filtered_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events", response_model=List[EventData])
async def get_events(start_date: str, end_date: str, category: Optional[str] = None):
    """Get major events for a specific date range and optional category"""
    try:
        # Path to events data in S3
        s3_path = "analytics/events"
        
        # In a real implementation, you would query and filter the data
        # This is a placeholder for demonstration
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=s3_path
        )
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Filter by date range and category if provided
        filtered_data = [
            d for d in data 
            if start_date <= d["date"] <= end_date and
            (category is None or d["category"] == category)
        ]
        
        return filtered_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keywords", response_model=List[KeywordData])
async def get_keywords(subreddit: str, timeframe: str):
    """Get top keywords for a specific subreddit and timeframe"""
    try:
        # Path to keywords data in S3
        s3_path = f"analytics/keywords/{subreddit}/{timeframe}"
        
        # In a real implementation, you would query and filter the data
        # This is a placeholder for demonstration
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=s3_path
        )
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subreddits", response_model=List[str])
async def get_subreddits():
    """Get list of available subreddits"""
    try:
        # In a real implementation, you would query the available subreddits
        # This is a placeholder for demonstration
        return ["askreddit", "politics", "science", "technology", "worldnews"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 