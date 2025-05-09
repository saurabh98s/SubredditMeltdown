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
import re
from collections import Counter, defaultdict

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
    allow_origins=["*"],
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
    impact_score: Optional[float] = None

class EventCorrelationData(BaseModel):
    event: EventData
    sentiment_before: float
    sentiment_after: float
    sentiment_change: float
    related_keywords: List[str]
    conversation_samples: List[str]

class KeywordData(BaseModel):
    keyword: str
    weight: float
    timeframe: str
    subreddit: str

class SentimentTimeseriesData(BaseModel):
    date: str
    avg_sentiment: float
    post_count: int
    events: List[EventData] = []

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
    category: Optional[str] = Query(None, description="Event category"),
    with_impact: bool = Query(False, description="Include impact scores if available")
):
    """Get events for a specific date range and optional category with impact scores"""
    try:
        # Find events in the period
        events = find_events_in_period(start_date, end_date)
        
        # Filter by category if provided
        if category:
            events = [e for e in events if e["category"] == category]
            
        # Create EventData objects
        event_data = []
        for event in events:
            event_obj = EventData(
                date=event["date"],
                event=event["event"],
                category=event["category"]
            )
            
            # Add impact score if requested and available
            if with_impact and "impact_score" in event:
                event_obj.impact_score = event["impact_score"]
                
            event_data.append(event_obj)
            
        return event_data
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keywords", response_model=List[KeywordData])
async def get_keywords(
    subreddit: str = Query(..., description="Subreddit name"),
    timeframe: str = Query(..., description="Timeframe (daily, weekly, monthly)")
):
    """Get top meaningful keywords for a specific subreddit and timeframe"""
    try:
        # First try to get from word_analysis directory
        s3_path = f"analytics/word_analysis/positive_words_{subreddit}"
        logger.info(f"Attempting to read positive words from {s3_path}")
        
        # Read parquet data from MinIO
        df = read_parquet_from_minio(bucket_name, s3_path)
        
        if df.empty:
            logger.info(f"No positive words found, trying negative words")
            # Try negative words
            s3_path = f"analytics/word_analysis/negative_words_{subreddit}"
            logger.info(f"Attempting to read negative words from {s3_path}")
            df = read_parquet_from_minio(bucket_name, s3_path)
            
        if df.empty:
            logger.warning(f"No keyword data found for subreddit: {subreddit}")
            return []
            
        # Log schema and data info
        logger.info(f"Keywords DataFrame columns: {df.columns.tolist()}")
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"Sample data:\n{df.head(3).to_string()}")
        
        # Log value counts and statistics
        for col in df.columns:
            logger.info(f"\nColumn '{col}' statistics:")
            logger.info(f"Null values: {df[col].isnull().sum()}")
            logger.info(f"Unique values: {df[col].nunique()}")
            if df[col].dtype in ['int64', 'float64']:
                logger.info(f"Numeric stats:\n{df[col].describe()}")
            elif df[col].dtype == 'object':
                logger.info(f"Top 5 most common values:\n{df[col].value_counts().head()}")
        
        # Ensure necessary columns exist
        if 'word' not in df.columns or 'avg_sentiment' not in df.columns or 'count' not in df.columns:
            logger.warning(f"Missing required columns in keyword data. Available columns: {df.columns.tolist()}")
            return []
            
        # Sort by count (descending)
        logger.info("Sorting by count...")
        df = df.sort_values(by='count', ascending=False)
        logger.info(f"Top 5 words by count:\n{df[['word', 'count', 'avg_sentiment']].head().to_string()}")
        
        # Comprehensive stop words list
        stop_words = {
            'that', 'have', 'they', 'this', 'with', 'just', 'your', 'like', 'what', 'about', 
            'more', 'their', 'because', "it's", 'would', "don't", 'from', 'when', 'will', 
            'even', 'some', 'there', 'think', 'than', 'make', 'want', 'only', 'them', 'being',
            'then', 'much', 'know', 'need', 'really', 'could', 'other', 'most', "you're",
            'still', 'into', 'also', 'should', 'where', 'been', 'were', 'which', 'these',
            'those', 'does', "doesn't", 'doing', 'done', 'each', 'every', 'gets', 'getting',
            'goes', 'going', 'came', 'come', 'comes', 'coming', 'here', 'herself', 'himself',
            'itself', 'myself', 'yourself', 'ourselves', 'themselves', 'very', 'well', 'says',
            'said', 'saying', 'tell', 'told', 'tells', 'telling', 'while', 'years', 'days',
            'months', 'week', 'weeks', 'month', 'year', 'hours', 'hour', 'minutes', 'minute',
            'always', 'never', 'sometimes', 'often', 'rarely', 'seem', 'seems', 'seemed',
            'anybody', 'everyone', 'somebody', 'nobody', 'everything', 'nothing', 'anything',
            'somewhere', 'anywhere', 'everywhere', 'nowhere', 'whatever', 'whoever', 'whenever',
            'however', 'whichever', 'anyone', 'someone', 'thing', 'things', 'stuff', 'ever',
            'especially', 'specifically', 'actually', 'basically', 'certainly', 'definitely',
            'absolutely', 'totally', 'completely', 'entirely', 'literally', 'really', 'quite',
            'rather', 'somewhat', 'somehow', 'such', 'that', 'this', 'these', 'those', 'same'
        }
        
        # Filter out common stop words
        df = df[~df['word'].str.lower().isin(stop_words)]
        
        # Filter out single-letter words and numbers
        df = df[~df['word'].str.match(r'^\d+$')]  # Filter numbers
        df = df[df['word'].str.len() > 2]  # Filter single/double letter words
        
        # Take top keywords
        top_df = df.head(50)
        logger.info(f"Selected top {len(top_df)} keywords")
        
        # Convert to the expected format
        keywords = []
        for _, row in top_df.iterrows():
            try:
                keyword = KeywordData(
                    keyword=row['word'],
                    weight=float(row['count']),
                    timeframe=timeframe,
                    subreddit=subreddit
                )
                keywords.append(keyword)
            except Exception as e:
                logger.error(f"Error converting row to KeywordData: {str(e)}")
                logger.error(f"Problematic row: {row.to_dict()}")
                continue
            
        logger.info(f"Returning {len(keywords)} keywords")
        return keywords
            
    except Exception as e:
        logger.error(f"Error retrieving keyword data: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subreddit/stats", response_model=Dict[str, Any])
async def get_subreddit_stats(
    subreddit: str = Query(..., description="Subreddit name"),
    period: str = Query("month", description="Period to analyze (week, month, year)")
):
    """Get enhanced statistics for a specific subreddit including event correlation"""
    try:
        # First check if the subreddit exists
        subreddits = await get_subreddits()
        if subreddit not in subreddits:
            raise HTTPException(status_code=404, detail=f"Subreddit '{subreddit}' not found")
        
        # Determine date range based on period
        today = datetime.now()
        if period == "week":
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        elif period == "year":
            start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        else:  # month is default
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            
        end_date = today.strftime("%Y-%m-%d")
        
        # Get sentiment data for both submissions and comments
        submissions_sentiment = await get_sentiment(subreddit, start_date, end_date, "submissions")
        comments_sentiment = await get_sentiment(subreddit, start_date, end_date, "comments")
        
        # Get overall sentiment
        overall_sentiment = {
            "submissions": sum(item.avg_sentiment * item.post_count for item in submissions_sentiment) / 
                           max(1, sum(item.post_count for item in submissions_sentiment)) if submissions_sentiment else 0,
            "comments": sum(item.avg_sentiment * item.post_count for item in comments_sentiment) / 
                        max(1, sum(item.post_count for item in comments_sentiment)) if comments_sentiment else 0
        }
        
        # Get event correlations
        correlations = await get_event_correlation(subreddit, start_date, end_date, "submissions")
        
        # Get keywords
        keywords_data = await get_keywords(subreddit, "weekly")
        
        # Calculate sentiment trends
        trends = {
            "submissions": "neutral",
            "comments": "neutral"
        }
        
        for content_type, sentiment_data in [("submissions", submissions_sentiment), ("comments", comments_sentiment)]:
            if sentiment_data and len(sentiment_data) > 1:
                first_half = sentiment_data[:len(sentiment_data)//2]
                second_half = sentiment_data[len(sentiment_data)//2:]
                
                first_avg = sum(item.avg_sentiment * item.post_count for item in first_half) / max(1, sum(item.post_count for item in first_half)) if first_half else 0
                second_avg = sum(item.avg_sentiment * item.post_count for item in second_half) / max(1, sum(item.post_count for item in second_half)) if second_half else 0
                
                if second_avg - first_avg > 0.1:
                    trends[content_type] = "positive"
                elif first_avg - second_avg > 0.1:
                    trends[content_type] = "negative"
        
        # Build response
        stats = {
            "subreddit": subreddit,
            "analysis_period": {
                "start_date": start_date,
                "end_date": end_date,
                "period": period
            },
            "activity": {
                "submission_count": sum(item.post_count for item in submissions_sentiment) if submissions_sentiment else 0,
                "comment_count": sum(item.post_count for item in comments_sentiment) if comments_sentiment else 0
            },
            "sentiment": {
                "overall": (overall_sentiment["submissions"] + overall_sentiment["comments"]) / 2,
                "submissions": {
                    "current": submissions_sentiment[-1].avg_sentiment if submissions_sentiment else 0,
                    "trend": trends["submissions"],
                    "history": [{"date": item.date, "sentiment": item.avg_sentiment, "count": item.post_count} 
                               for item in submissions_sentiment]
                },
                "comments": {
                    "current": comments_sentiment[-1].avg_sentiment if comments_sentiment else 0,
                    "trend": trends["comments"],
                    "history": [{"date": item.date, "sentiment": item.avg_sentiment, "count": item.post_count} 
                               for item in comments_sentiment]
                }
            },
            "events": {
                "correlated_events": [
                    {
                        "date": item.event.date,
                        "event": item.event.event,
                        "category": item.event.category,
                        "sentiment_change": item.sentiment_change,
                        "impact_score": item.event.impact_score or abs(item.sentiment_change),
                        "keywords": item.related_keywords
                    } for item in correlations[:5]  # Top 5 correlated events
                ],
                "total_significant_events": len(correlations)
            },
            "top_keywords": [
                {
                    "keyword": item.keyword,
                    "weight": item.weight
                } for item in keywords_data[:10]  # Top 10 keywords
            ] if keywords_data else []
        }
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving subreddit stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trending", response_model=List[Dict[str, Any]])
async def get_trending_subreddits():
    """Get trending subreddits based on recent activity, sentiment, and event impact"""
    try:
        # Get list of all subreddits
        subreddits = await get_subreddits()
        
        # Current date for reference
        today = datetime.now()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        # For each subreddit, get recent stats
        trending = []
        for subreddit in subreddits[:10]:  # Limit to 10 for performance
            try:
                # Get basic stats
                stats = await get_subreddit_stats(subreddit, "month")
                
                # Get event correlations
                correlations = await get_event_correlation(subreddit, start_date, end_date, "submissions")
                
                # Find most impactful event
                most_impactful_event = None
                if correlations:
                    most_impactful = max(correlations, key=lambda x: abs(x.sentiment_change))
                    most_impactful_event = {
                        "date": most_impactful.event.date,
                        "event": most_impactful.event.event,
                        "impact": most_impactful.sentiment_change
                    }
                
                # Add to trending list
                trending.append({
                    "subreddit": subreddit,
                    "sentiment_trend": stats["sentiment"]["submissions"]["trend"],
                    "current_sentiment": stats["sentiment"]["submissions"]["current"],
                    "post_count": stats["activity"]["submission_count"],
                    "top_keywords": [kw["keyword"] for kw in stats["top_keywords"][:3]] if stats["top_keywords"] else [],
                    "most_impactful_event": most_impactful_event
                })
            except Exception as e:
                logger.error(f"Error getting stats for {subreddit}: {str(e)}")
                continue
        
        # Sort by absolute sentiment change or current sentiment if no event impact
        trending.sort(key=lambda x: abs(x["most_impactful_event"]["impact"]) if x["most_impactful_event"] else abs(x["current_sentiment"]), reverse=True)
        
        return trending
    except Exception as e:
        logger.error(f"Error retrieving trending subreddits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions for event correlation
def load_events_data():
    """Load events data from MinIO or use default data focusing on Oct-Nov 2019/2020"""
    try:
        # Try to get from S3/MinIO
        try:
            events_key = "analytics/events"
            response = s3_client.get_object(Bucket=bucket_name, Key=events_key)
            events = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"Loaded {len(events)} events from MinIO")
            return events
        except ClientError as e:
            logger.warning(f"Could not load events from MinIO: {str(e)}")
            
        # Fallback to hardcoded events for Oct-Nov 2019/2020
        default_events = [
            {"date": "2019-10-01", "event": "Reddit launches AITA (Am I The Asshole) community awards", "category": "platform"},
            {"date": "2019-10-10", "event": "Blizzard bans Hearthstone player for supporting Hong Kong protests", "category": "gaming"},
            {"date": "2019-10-15", "event": "Reddit implements new award system sitewide", "category": "platform"},
            {"date": "2019-10-23", "event": "Reddit's mobile app reaches 50 million downloads", "category": "platform"},
            {"date": "2019-11-05", "event": "Reddit introduces 'Community Points' in test subreddits", "category": "platform"},
            {"date": "2019-11-13", "event": "Reddit's 'Popular' tab algorithm changes announced", "category": "platform"},
            {"date": "2019-11-20", "event": "Cybertruck unveiling by Tesla", "category": "technology"},
            {"date": "2019-11-25", "event": "Major Reddit outage affecting multiple subreddits", "category": "platform"},
            {"date": "2020-10-05", "event": "Reddit introduces new content warning labels", "category": "platform"},
            {"date": "2020-10-12", "event": "Reddit launches new features for moderators", "category": "platform"},
            {"date": "2020-10-15", "event": "Reddit experiences widespread content filtering issue", "category": "platform"},
            {"date": "2020-10-28", "event": "U.S. Senate hearings with social media CEOs", "category": "politics"},
            {"date": "2020-11-03", "event": "U.S. Presidential Election", "category": "politics"},
            {"date": "2020-11-07", "event": "U.S. Election results called for Biden", "category": "politics"},
            {"date": "2020-11-15", "event": "Reddit updates content policy enforcement", "category": "platform"},
            {"date": "2020-11-25", "event": "Reddit experiences moderation tool outage", "category": "platform"},
        ]
        logger.info(f"Using default {len(default_events)} events")
        return default_events
        
    except Exception as e:
        logger.error(f"Error loading events: {str(e)}")
        return []

def find_events_in_period(start_date, end_date, events=None):
    """Find events that occurred within a given date range"""
    if events is None:
        events = load_events_data()
        
    return [event for event in events 
            if start_date <= event["date"] <= end_date]

def calculate_sentiment_change(sentiment_data, event_date, window_days=3):
    """Calculate sentiment change before and after an event"""
    if not sentiment_data:
        return None, None, 0.0
        
    # Convert event_date to datetime
    event_dt = datetime.strptime(event_date, "%Y-%m-%d")
    
    # Get data before and after the event
    before_data = [item for item in sentiment_data 
                  if (event_dt - timedelta(days=window_days)).strftime("%Y-%m-%d") <= item.date < event_date]
    
    after_data = [item for item in sentiment_data 
                 if event_date <= item.date <= (event_dt + timedelta(days=window_days)).strftime("%Y-%m-%d")]
    
    # Calculate average sentiment before and after
    before_sentiment = sum(item.avg_sentiment * item.post_count for item in before_data) / max(1, sum(item.post_count for item in before_data)) if before_data else 0
    after_sentiment = sum(item.avg_sentiment * item.post_count for item in after_data) / max(1, sum(item.post_count for item in after_data)) if after_data else 0
    
    # Calculate the change
    sentiment_change = after_sentiment - before_sentiment
    
    return before_sentiment, after_sentiment, sentiment_change

def read_jsonl_samples(subreddit, start_date, end_date, limit=5, content_type="submissions"):
    """Read sample conversations from cleaned Parquet files for a given period"""
    try:
        # Try to get from S3 - using cleaned data instead of raw
        samples = []
        prefix = f"cleaned/{content_type}/{subreddit}"
        
        try:
            # List objects in the directory
            logger.info(f"Looking for cleaned data in {bucket_name}/{prefix}")
            response = s3_client.list_objects_v2(
                Bucket="mh-trends",
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"No objects found in {bucket_name}/{prefix}")
                return []
                
            # Find parquet files
            parquet_files = [obj['Key'] for obj in response['Contents'] 
                          if obj['Key'].endswith('.parquet') or obj['Key'].endswith('snappy.parquet')]
            
            if not parquet_files:
                logger.warning(f"No parquet files found in {bucket_name}/{prefix}")
                return []
                
            # Process each file to find samples
            for file_key in parquet_files[:5]:  # Limit files to check
                try:
                    logger.info(f"Reading parquet file {file_key}")
                    # Read parquet into a pandas dataframe
                    response = s3_client.get_object(Bucket="mh-trends", Key=file_key)
                    parquet_data = BytesIO(response['Body'].read())
                    
                    df = pq.read_table(parquet_data).to_pandas()
                    
                    # Process based on content type
                    if content_type == "submissions":
                        # Convert created_utc to datetime if it's a string or timestamp
                        if 'created_utc' in df.columns:
                            if df['created_utc'].dtype == 'object':
                                df['date'] = pd.to_datetime(df['created_utc'], unit='s').dt.strftime('%Y-%m-%d')
                            else:
                                df['date'] = pd.to_datetime(df['created_utc'].astype(float), unit='s').dt.strftime('%Y-%m-%d')
                        
                        # Filter by date range
                        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        
                        # Get samples
                        for _, row in filtered_df.sample(min(limit, len(filtered_df))).iterrows():
                            title = row.get('title', '')
                            selftext = row.get('selftext', '')
                            content = f"{title}\n{selftext}" if selftext and selftext not in ["[deleted]", "[removed]"] else title
                            
                            if content and len(content.strip()) > 20:
                                samples.append(content[:300] + "..." if len(content) > 300 else content)
                    else:  # comments
                        # Convert created_utc to datetime if it's a string or timestamp
                        if 'created_utc' in df.columns:
                            if df['created_utc'].dtype == 'object':
                                df['date'] = pd.to_datetime(df['created_utc'], unit='s').dt.strftime('%Y-%m-%d')
                            else:
                                df['date'] = pd.to_datetime(df['created_utc'].astype(float), unit='s').dt.strftime('%Y-%m-%d')
                        
                        # Filter by date range
                        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        
                        # Get samples
                        for _, row in filtered_df.sample(min(limit, len(filtered_df))).iterrows():
                            body = row.get('body', '')
                            
                            if body and body not in ["[deleted]", "[removed]"] and len(body.strip()) > 20:
                                samples.append(body[:300] + "..." if len(body) > 300 else body)
                    
                    # If we have enough samples, return
                    if len(samples) >= limit:
                        return samples
                except Exception as e:
                    logger.error(f"Error processing file {file_key}: {str(e)}")
                    continue
        except Exception as e:
            logger.warning(f"Error reading Parquet from S3: {str(e)}")
            
        # Return what we found
        return samples
    except Exception as e:
        logger.error(f"Error reading samples: {str(e)}")
        return []

def extract_related_keywords(samples, event, max_keywords=5):
    """Extract keywords from samples that might be related to the event"""
    if not samples:
        return []
        
    # Combine all samples into one text
    all_text = " ".join(samples).lower()
    
    # Get event words
    event_words = set(re.findall(r'\b\w{4,}\b', event.lower()))
    
    # Get words from the combined text
    words = re.findall(r'\b\w{4,}\b', all_text)
    
    # Count word frequencies
    word_counts = Counter(words)
    
    # Comprehensive stop words list
    stop_words = {
        'that', 'have', 'they', 'this', 'with', 'just', 'your', 'like', 'what', 'about', 
        'more', 'their', 'because', "it's", 'would', "don't", 'from', 'when', 'will', 
        'even', 'some', 'there', 'think', 'than', 'make', 'want', 'only', 'them', 'being',
        'then', 'much', 'know', 'need', 'really', 'could', 'other', 'most', "you're",
        'still', 'into', 'also', 'should', 'where', 'been', 'were', 'which', 'these',
        'those', 'does', "doesn't", 'doing', 'done', 'each', 'every', 'gets', 'getting',
        'goes', 'going', 'came', 'come', 'comes', 'coming', 'here', 'herself', 'himself',
        'itself', 'myself', 'yourself', 'ourselves', 'themselves', 'very', 'well', 'says',
        'said', 'saying', 'tell', 'told', 'tells', 'telling', 'while', 'years', 'days',
        'months', 'week', 'weeks', 'month', 'year', 'hours', 'hour', 'minutes', 'minute',
        'always', 'never', 'sometimes', 'often', 'rarely', 'seem', 'seems', 'seemed',
        'anybody', 'everyone', 'somebody', 'nobody', 'everything', 'nothing', 'anything',
        'somewhere', 'anywhere', 'everywhere', 'nowhere', 'whatever', 'whoever', 'whenever',
        'however', 'whichever', 'anyone', 'someone', 'thing', 'things', 'stuff', 'ever',
        'especially', 'specifically', 'actually', 'basically', 'certainly', 'definitely',
        'absolutely', 'totally', 'completely', 'entirely', 'literally', 'really', 'quite',
        'rather', 'somewhat', 'somehow', 'such', 'that', 'this', 'these', 'those', 'same'
    }
    
    # Filter keywords
    keywords = [(word, count) for word, count in word_counts.most_common(50) 
                if word not in stop_words and word not in event_words]
    
    return [word for word, _ in keywords[:max_keywords]]

@app.get("/events/correlation", response_model=List[EventCorrelationData])
async def get_event_correlation(
    subreddit: str = Query(..., description="Subreddit name"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    content_type: str = Query("submissions", description="Content type (submissions or comments)"),
    window_days: int = Query(3, description="Window days before/after event for correlation")
):
    """Get event correlation with sentiment changes for a specific subreddit and date range"""
    try:
        # Get sentiment data
        sentiment_data = await get_sentiment(subreddit, start_date, end_date, content_type)
        
        if not sentiment_data:
            return []
            
        # Find events in the period
        events = find_events_in_period(start_date, end_date)
        
        if not events:
            logger.warning(f"No events found for period {start_date} to {end_date}")
            return []
            
        # Calculate correlation for each event
        correlations = []
        for event in events:
            event_date = event["date"]
            
            # Calculate sentiment change
            before_sentiment, after_sentiment, sentiment_change = calculate_sentiment_change(
                sentiment_data, event_date, window_days
            )
            
            # Only include significant changes
            if abs(sentiment_change) < 0.05:
                continue
                
            # Find related conversations
            samples = read_jsonl_samples(
                subreddit,
                event_date,
                (datetime.strptime(event_date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d"),
                limit=5,
                content_type=content_type
            )
            
            # Extract related keywords
            related_keywords = extract_related_keywords(samples, event["event"])
            
            # Create correlation data
            correlation = EventCorrelationData(
                event=EventData(
                    date=event["date"],
                    event=event["event"],
                    category=event["category"],
                    impact_score=abs(sentiment_change)
                ),
                sentiment_before=before_sentiment,
                sentiment_after=after_sentiment,
                sentiment_change=sentiment_change,
                related_keywords=related_keywords,
                conversation_samples=samples
            )
            
            correlations.append(correlation)
            
        # Sort by impact (absolute sentiment change)
        correlations.sort(key=lambda x: abs(x.sentiment_change), reverse=True)
        
        return correlations
    except Exception as e:
        logger.error(f"Error calculating event correlation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sentiment/timeseries", response_model=List[SentimentTimeseriesData])
async def get_sentiment_timeseries(
    subreddit: str = Query(..., description="Subreddit name"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    content_type: str = Query("submissions", description="Content type (submissions or comments)"),
    include_events: bool = Query(True, description="Include events in the response")
):
    """Get sentiment timeseries with events for a specific subreddit and date range"""
    try:
        # Get sentiment data
        sentiment_data = await get_sentiment(subreddit, start_date, end_date, content_type)
        
        if not sentiment_data:
            return []
            
        # Get events if requested
        events = find_events_in_period(start_date, end_date) if include_events else []
        
        # Create event lookup by date
        event_lookup = defaultdict(list)
        for event in events:
            event_lookup[event["date"]].append(
                EventData(
                    date=event["date"],
                    event=event["event"],
                    category=event["category"]
                )
            )
            
        # Create timeseries with events
        timeseries = []
        for item in sentiment_data:
            timeseries.append(
                SentimentTimeseriesData(
                    date=item.date,
                    avg_sentiment=item.avg_sentiment,
                    post_count=item.post_count,
                    events=event_lookup.get(item.date, [])
                )
            )
            
        return timeseries
    except Exception as e:
        logger.error(f"Error retrieving sentiment timeseries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keywords/trending", response_model=Dict[str, List[KeywordData]])
async def get_trending_keywords(
    subreddit: str = Query(..., description="Subreddit name"),
    event_date: Optional[str] = Query(None, description="Event date to find keywords around (YYYY-MM-DD)"),
    timeframe: str = Query("weekly", description="Timeframe (daily, weekly, monthly)")
):
    """Get trending meaningful keywords for a specific subreddit, with option to focus around a specific event"""
    try:
        # If event_date is provided, focus on keywords around that date
        if event_date:
            # Define date range around the event
            event_dt = datetime.strptime(event_date, "%Y-%m-%d")
            start_date = (event_dt - timedelta(days=3)).strftime("%Y-%m-%d")
            end_date = (event_dt + timedelta(days=3)).strftime("%Y-%m-%d")
            
            # Get before and after keywords
            before_keywords = await get_keywords(subreddit, timeframe)
            
            # Get samples from around the event
            samples = read_jsonl_samples(
                subreddit,
                start_date,
                end_date,
                limit=30,
                content_type="submissions"
            )
            
            # If no samples, just return the regular keywords
            if not samples:
                return {"trending": before_keywords}
                
            # Extract event-related keywords
            all_text = " ".join(samples).lower()
            words = re.findall(r'\b\w{4,}\b', all_text)
            word_counts = Counter(words)
            
            # Comprehensive stop word list
            stop_words = {
                'that', 'have', 'they', 'this', 'with', 'just', 'your', 'like', 'what', 'about', 
                'more', 'their', 'because', "it's", 'would', "don't", 'from', 'when', 'will', 
                'even', 'some', 'there', 'think', 'than', 'make', 'want', 'only', 'them', 'being',
                'then', 'much', 'know', 'need', 'really', 'could', 'other', 'most', "you're",
                'still', 'into', 'also', 'should', 'where', 'been', 'were', 'which', 'these',
                'those', 'does', "doesn't", 'doing', 'done', 'each', 'every', 'gets', 'getting',
                'goes', 'going', 'came', 'come', 'comes', 'coming', 'here', 'herself', 'himself',
                'itself', 'myself', 'yourself', 'ourselves', 'themselves', 'very', 'well', 'says',
                'said', 'saying', 'tell', 'told', 'tells', 'telling', 'while', 'years', 'days',
                'months', 'week', 'weeks', 'month', 'year', 'hours', 'hour', 'minutes', 'minute',
                'always', 'never', 'sometimes', 'often', 'rarely', 'seem', 'seems', 'seemed',
                'anybody', 'everyone', 'somebody', 'nobody', 'everything', 'nothing', 'anything',
                'somewhere', 'anywhere', 'everywhere', 'nowhere', 'whatever', 'whoever', 'whenever',
                'however', 'whichever', 'anyone', 'someone', 'thing', 'things', 'stuff', 'ever',
                'especially', 'specifically', 'actually', 'basically', 'certainly', 'definitely',
                'absolutely', 'totally', 'completely', 'entirely', 'literally', 'really', 'quite',
                'rather', 'somewhat', 'somehow', 'such', 'that', 'this', 'these', 'those', 'same'
            }
            
            # Create keyword objects for event-related words
            event_keywords = []
            for word, count in word_counts.most_common(100):
                # Filter out stop words, single/double letter words, and numbers
                if (word not in stop_words and 
                    len(word) > 2 and 
                    not word.isdigit() and 
                    count > 1):
                    event_keywords.append(
                        KeywordData(
                            keyword=word,
                            weight=float(count),
                            timeframe="event",
                            subreddit=subreddit
                        )
                    )
            
            return {
                "trending": before_keywords[:20],
                "event_related": event_keywords[:20]
            }
        else:
            # Just return regular keywords
            keywords = await get_keywords(subreddit, timeframe)
            return {"trending": keywords}
    except Exception as e:
        logger.error(f"Error retrieving trending keywords: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations", response_model=Dict[str, Any])
async def get_conversations(
    subreddit: str = Query(..., description="Subreddit name"),
    event_date: str = Query(..., description="Event date (YYYY-MM-DD)"),
    window_days: int = Query(3, description="Days before/after the event to include"),
    limit: int = Query(20, description="Maximum number of conversations to return")
):
    """Get raw conversation data around a specific event date including both submissions and comments"""
    try:
        # Calculate date range
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
        start_date = (event_dt - timedelta(days=window_days)).strftime("%Y-%m-%d")
        end_date = (event_dt + timedelta(days=window_days)).strftime("%Y-%m-%d")
        
        # Get event info - first try loading from events.json
        event_info = {"event": "Unknown event", "category": "unknown"}
        try:
            # Try to load from events.json file
            with open("api/mock_data/events.json", "r") as f:
                events_data = json.load(f)
                
            # Find event matching the date
            for event in events_data:
                if event.get("date") == event_date:
                    event_info = event
                    break
                    
            if event_info["event"] == "Unknown event":
                # Fall back to find_events_in_period
                events = find_events_in_period(event_date, event_date)
                if events:
                    event_info = events[0]
        except Exception as e:
            logger.warning(f"Error reading events.json: {str(e)}, falling back to default events")
            events = find_events_in_period(event_date, event_date)
            if events:
                event_info = events[0]
        
        # Extract key terms from the event description for content filtering
        event_keywords = []
        if event_info and "event" in event_info:
            # Extract meaningful keywords from event description
            event_desc = event_info["event"].lower()
            # Remove common words
            stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about'}
            event_keywords = [word for word in re.findall(r'\b\w{3,}\b', event_desc) 
                             if word not in stop_words]
            logger.info(f"Extracted event keywords: {event_keywords}")
        
        # Default empty response with event info
        default_response = {
            "event": {
                "date": event_date,
                "name": event_info.get("event", "Unknown event"),
                "category": event_info.get("category", "unknown"),
                "impact_score": event_info.get("impact_score", 0.0)
            },
            "conversations": []
        }
        
        # Process both submissions and comments
        all_conversations = []
        found_data = False  # Track if we found any data regardless of date filter
        
        # Define sentiment analyzer function for inline analysis
        def quick_sentiment(text):
            if not text or not isinstance(text, str):
                return 0
            try:
                # Import here to ensure it's available
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                analyzer = SentimentIntensityAnalyzer()
                scores = analyzer.polarity_scores(text)
                return scores['compound']
            except Exception as e:
                logger.error(f"Sentiment analysis error: {str(e)}")
                return 0
        
        # Helper function to check if content is related to event
        def is_event_related(text, event_keywords):
            if not text or not isinstance(text, str) or not event_keywords:
                return False
            
            text = text.lower()
            # Check if any event keywords are in the text
            return any(keyword in text for keyword in event_keywords)
        
        # Process both content types
        for content_type in ["submissions", "comments"]:
            try:
                # Define S3 path for cleaned data
                data_path = f"cleaned/{content_type}/{subreddit}"
                logger.info(f"Looking for cleaned data in {bucket_name}/{data_path}")
                
                # List objects in the directory
                response = s3_client.list_objects_v2(
                    Bucket="mh-trends",
                    Prefix=data_path
                )
                
                if 'Contents' not in response:
                    logger.warning(f"No objects found in {bucket_name}/{data_path}")
                    continue
                    
                # Find parquet files
                parquet_files = [obj['Key'] for obj in response['Contents'] 
                              if obj['Key'].endswith('.parquet') or obj['Key'].endswith('snappy.parquet')]
                
                if not parquet_files:
                    logger.warning(f"No parquet files found in {bucket_name}/{data_path}")
                    continue
                
                # Process parquet files to find conversations
                for file_key in parquet_files[:5]:  # Limit to first 5 files for performance
                    try:
                        logger.info(f"Reading parquet file {file_key}")
                        # Read parquet into a pandas dataframe
                        response = s3_client.get_object(Bucket="mh-trends", Key=file_key)
                        parquet_data = BytesIO(response['Body'].read())
                        
                        df = pq.read_table(parquet_data).to_pandas()
                        
                        # Convert created_utc to datetime - fix deprecation warning
                        if 'created_utc' in df.columns:
                            if df['created_utc'].dtype == 'object':
                                # First convert to numeric explicitly to avoid the warning
                                df['created_utc_numeric'] = pd.to_numeric(df['created_utc'], errors='coerce')
                                df['date'] = pd.to_datetime(df['created_utc_numeric'], unit='s').dt.strftime('%Y-%m-%d')
                            else:
                                df['date'] = pd.to_datetime(df['created_utc'].astype(float), unit='s').dt.strftime('%Y-%m-%d')
                        else:
                            logger.warning(f"No created_utc column found in {file_key}")
                            continue
                        
                        # Keep track of all data before date filtering
                        if not df.empty:
                            found_data = True
                            
                        # First try with date filter
                        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        
                        # If no data in date range but we have data, use without filtering
                        if filtered_df.empty and not df.empty:
                            logger.info(f"No conversations found within date range in {file_key}. Using unfiltered data.")
                            filtered_df = df.sample(min(50, len(df))) if len(df) > 0 else df
                        
                        if filtered_df.empty:
                            logger.info(f"No conversations found in {file_key}")
                            continue
                        
                        # Extract content based on type
                        if content_type == "submissions":
                            for _, item in filtered_df.iterrows():
                                try:
                                    title = str(item.get('title', '')) if item.get('title') is not None else ''
                                    body = str(item.get('selftext', '')) if item.get('selftext') is not None else ''
                                    content = f"{title}\n{body}" if body and body not in ["[deleted]", "[removed]"] else title
                                    url = str(item.get('url', '')) if item.get('url') is not None else ''
                                    
                                    # Skip if no meaningful content
                                    if not title or len(title) < 5:
                                        continue
                                    
                                    # Check if content is related to the event
                                    if event_keywords and not is_event_related(content, event_keywords):
                                        continue
                                        
                                    # Calculate sentiment
                                    sentiment = quick_sentiment(content)
                                    
                                    item_date = item.get('date')
                                    if isinstance(item_date, pd.Timestamp):
                                        item_date = item_date.strftime('%Y-%m-%d')
                                    
                                    # Calculate days from event only if within range
                                    days_from_event = 0
                                    try:
                                        days_from_event = (datetime.strptime(item_date, "%Y-%m-%d") - event_dt).days
                                    except:
                                        pass
                                    
                                    # Add to conversations
                                    all_conversations.append({
                                        "id": str(item.get('id', '')),
                                        "date": item_date,
                                        "title": title,
                                        "content": body[:500] + "..." if body and len(body) > 500 else body,
                                        "url": url,
                                        "author": str(item.get('author', '[deleted]')),
                                        "score": int(item.get('score', 0)) if item.get('score') is not None else 0,
                                        "sentiment": float(sentiment),
                                        "days_from_event": days_from_event,
                                        "type": "submission",
                                        "event_relevant": True  # Mark as event relevant since we filtered
                                    })
                                except Exception as e:
                                    logger.error(f"Error processing submission item: {str(e)}")
                                    continue
                        else:  # comments
                            for _, item in filtered_df.iterrows():
                                try:
                                    body = str(item.get('body', '')) if item.get('body') is not None else ''
                                    
                                    # Skip if no meaningful content
                                    if not body or body in ["[deleted]", "[removed]"] or len(body) < 5:
                                        continue
                                    
                                    # Check if content is related to the event
                                    if event_keywords and not is_event_related(body, event_keywords):
                                        continue
                                        
                                    # Calculate sentiment
                                    sentiment = quick_sentiment(body)
                                    
                                    item_date = item.get('date')
                                    if isinstance(item_date, pd.Timestamp):
                                        item_date = item_date.strftime('%Y-%m-%d')
                                    
                                    # Calculate days from event only if within range
                                    days_from_event = 0
                                    try:
                                        days_from_event = (datetime.strptime(item_date, "%Y-%m-%d") - event_dt).days
                                    except:
                                        pass
                                    
                                    # Add to conversations
                                    all_conversations.append({
                                        "id": str(item.get('id', '')),
                                        "date": item_date,
                                        "content": body[:500] + "..." if len(body) > 500 else body,
                                        "author": str(item.get('author', '[deleted]')),
                                        "score": int(item.get('score', 0)) if item.get('score') is not None else 0,
                                        "parent_id": str(item.get('parent_id', '')),
                                        "link_id": str(item.get('link_id', '')),
                                        "sentiment": float(sentiment),
                                        "days_from_event": days_from_event,
                                        "type": "comment",
                                        "event_relevant": True  # Mark as event relevant since we filtered
                                    })
                                except Exception as e:
                                    logger.error(f"Error processing comment item: {str(e)}")
                                    continue
                    except Exception as e:
                        logger.error(f"Error processing file {file_key}: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Error processing {content_type}: {str(e)}")
                continue
        
        # If we have conversations, sort and return them
        if all_conversations:
            # Sort by relevance (days from event, score, and sentiment impact)
            all_conversations.sort(key=lambda x: (abs(x.get('days_from_event', 0)), x.get('score', 0), abs(x.get('sentiment', 0))), reverse=True)
            
            # Log sentiment values for debugging
            for i, conv in enumerate(all_conversations[:5]):
                logger.info(f"Conversation {i+1} sentiment: {conv.get('sentiment')}")
            
            # Return result with conversations
            return {
                "event": {
                    "date": event_date,
                    "name": event_info.get("event", "Unknown event"),
                    "category": event_info.get("category", "unknown"),
                    "impact_score": event_info.get("impact_score", 0.0)
                },
                "conversations": all_conversations[:limit],
                "matched_conversations_count": len(all_conversations)
            }
        else:
            # Return default response if no conversations found
            return default_response
            
    except Exception as e:
        logger.error(f"Error retrieving conversations: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        return {
            "event": {
                "date": event_date,
                "name": "Unknown event",
                "category": "unknown"
            },
            "conversations": []
        }

@app.get("/events/generate", response_model=List[EventData])
async def generate_events(
    subreddit: str = Query(..., description="Subreddit name"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    content_type: str = Query("submissions", description="Content type (submissions or comments)"),
    min_sentiment_change: float = Query(0.1, description="Minimum sentiment change to consider as an event"),
    window_size: int = Query(3, description="Size of window to check for sentiment changes (in days)")
):
    """
    Dynamically generate events based on significant sentiment changes in the data.
    This helps identify potentially important dates even if they're not in the predefined events list.
    """
    try:
        # Get sentiment data for the specified period
        sentiment_data = await get_sentiment(subreddit, start_date, end_date, content_type)
        
        if not sentiment_data or len(sentiment_data) < window_size + 1:
            return []
        
        # Sort by date
        sentiment_data.sort(key=lambda x: x.date)
        
        # Calculate rolling sentiment and find significant changes
        generated_events = []
        
        for i in range(window_size, len(sentiment_data)):
            # Calculate average sentiment before current point
            before_window = sentiment_data[i-window_size:i]
            before_sentiment = sum(item.avg_sentiment * item.post_count for item in before_window) / max(1, sum(item.post_count for item in before_window))
            
            # Get current point
            current = sentiment_data[i]
            
            # Calculate sentiment change
            sentiment_change = current.avg_sentiment - before_sentiment
            
            # If change is significant, consider it an event
            if abs(sentiment_change) >= min_sentiment_change:
                # Determine event type based on direction of change
                event_type = "significant_increase" if sentiment_change > 0 else "significant_decrease"
                
                # Try to get keywords for this period to enhance event description
                event_keywords = []
                try:
                    # Calculate a 3-day window around the event
                    event_date = current.date
                    event_dt = datetime.strptime(event_date, "%Y-%m-%d")
                    event_start = (event_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                    event_end = (event_dt + timedelta(days=1)).strftime("%Y-%m-%d")
                    
                    # Get samples for this period
                    samples = read_jsonl_samples(subreddit, event_start, event_end, limit=10, content_type=content_type)
                    
                    # Extract keywords
                    if samples:
                        # Extract keywords from the samples
                        all_text = " ".join(samples).lower()
                        words = re.findall(r'\b\w{4,}\b', all_text)
                        word_counts = Counter(words)
                        
                        # Filter common words
                        stop_words = {
                            'that', 'have', 'they', 'this', 'with', 'just', 'your', 'like', 'what', 'about', 
                            'more', 'their', 'because', "it's", 'would', "don't", 'from', 'when', 'will', 
                            'even', 'some', 'there', 'think', 'than', 'make', 'want', 'only', 'them', 'being',
                            'then', 'much', 'know', 'need', 'really', 'could', 'other', 'most', "you're"
                        }
                        event_keywords = [word for word, count in word_counts.most_common(5) 
                                         if word not in stop_words and len(word) > 3]
                except Exception as e:
                    logger.error(f"Error extracting keywords for generated event: {str(e)}")
                
                # Create event description
                if event_keywords:
                    topics = ", ".join(event_keywords)
                    event_description = f"{'Positive' if sentiment_change > 0.45 else 'Negative'} sentiment shift in r/{subreddit} around topics: {topics}"
                else:
                    event_description = f"{'Positive' if sentiment_change > 0.45 else 'Negative'} sentiment shift detected in r/{subreddit}"
                
                # Determine category
                if "politic" in " ".join(event_keywords).lower():
                    category = "politics"
                elif any(tech in " ".join(event_keywords).lower() for tech in ["tech", "software", "code", "program", "computer"]):
                    category = "technology"
                elif any(game in " ".join(event_keywords).lower() for game in ["game", "play", "gaming"]):
                    category = "gaming"
                else:
                    category = "community"
                
                # Create event object
                event = EventData(
                    date=current.date,
                    event=event_description,
                    category=category,
                    impact_score=abs(sentiment_change)
                )
                
                generated_events.append(event)
        
        # Merge with official events
        official_events = find_events_in_period(start_date, end_date)
        official_event_dates = [e["date"] for e in official_events]
        
        # Only include generated events that don't overlap with official events
        filtered_events = [e for e in generated_events if e.date not in official_event_dates]
        
        # Sort by date
        filtered_events.sort(key=lambda x: x.date)
        
        return filtered_events
        
    except Exception as e:
        logger.error(f"Error generating events: {str(e)}")
        logger.exception("Full exception:")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 