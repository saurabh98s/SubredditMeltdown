# Reddit Meltdown Analysis

A comprehensive data analysis platform for tracking sentiment trends and keyword patterns across Reddit subreddits over time, with correlation to major world events.

## Project Structure

- `data_ingestion/`: Scripts for downloading and ingesting Reddit data
- `pyspark_jobs/`: PySpark data processing and analysis jobs
- `backend/`: FastAPI backend service
- `frontend/`: Next.js frontend application
- `infra/`: Infrastructure configuration (Docker Compose)
- `docs/`: Documentation
- `tests/`: Tests

## Features

- Download and preprocess Reddit data from Arctic Shift archives
- Sentiment analysis on Reddit posts and comments
- Correlation of sentiment with major world events
- Keyword extraction and tracking over time
- Interactive dashboard with time-series visualization and filters

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Node.js 16+

## Setup and Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd SubredditMeltdown
```

### 2. Environment Setup

Create necessary directories:

```bash
mkdir -p data/raw data/processed data/analytics
```

### 3. Start the Docker environment

```bash
docker-compose up -d
```

This will start:
- Zookeeper and Kafka for streaming
- Spark master and worker nodes
- MinIO (S3-compatible storage)
- Backend API
- Frontend app

## Data Processing Workflow

### 1. Download Reddit data

```bash
python data_ingestion/download_arctic_shift.py --start-date 2020-01 --end-date 2020-12
```

### 2. Clean and preprocess the data

```bash
docker exec -it spark-master /opt/bitnami/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/bitnami/spark/jobs/clean_posts.py \
  --input-dir /data/raw \
  --output-dir /data/processed \
  --upload-to-s3
```

### 3. Run sentiment analysis

```bash
docker exec -it spark-master /opt/bitnami/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/bitnami/spark/jobs/sentiment_analysis.py \
  --input-dir /data/processed \
  --output-dir /data/analytics/sentiment \
  --upload-to-s3
```

### 4. Extract keywords

```bash
docker exec -it spark-master /opt/bitnami/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/bitnami/spark/jobs/keyword_extraction.py \
  --input-dir /data/processed \
  --output-dir /data/analytics/keywords \
  --timeframe monthly \
  --upload-to-s3
```

### 5. Correlate sentiment with events

```bash
docker exec -it spark-master /opt/bitnami/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/bitnami/spark/jobs/event_correlation.py \
  --sentiment-path /data/analytics/sentiment/combined_sentiment \
  --events-path /data/events.csv \
  --output-dir /data/analytics/events_correlation \
  --upload-to-s3
```

## Accessing the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- Spark UI: http://localhost:8080

## Technical Details

### Backend

The backend is built with FastAPI and provides:
- Sentiment data for subreddits over time
- Major event data for correlations
- Keyword data by timeframe
- Available subreddit listings

### Frontend

The frontend is built with Next.js and features:
- Interactive time-series charts for sentiment
- Subreddit and date range filters
- Event overlays on charts
- Keyword visualization

### Data Storage

- Raw data: Local filesystem and S3-compatible storage (MinIO)
- Processed data: Parquet files in S3-compatible storage
- Analytics results: JSON files in S3-compatible storage

## License

[MIT License](LICENSE)