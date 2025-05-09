# SubredditMeltdown PySpark Pipeline

This directory contains PySpark jobs for processing Reddit data, specifically focusing on posts and comments.

## Prerequisites

- Python 3.8+
- PySpark 3.3.0+
- MinIO instance (or S3 compatible storage)

## Quick Start

```bash
# Make the scripts executable
chmod +x pipeline.sh job_wrapper.py *.py

# Place your raw Reddit data in the data/raw directory
mkdir -p /s/WORK/PROJECTS/SubredditMeltdown/data/raw

# Run the complete pipeline
./pipeline.sh
```

## Directory Structure

The pipeline creates and uses the following directory structure:

```
/s/WORK/PROJECTS/SubredditMeltdown/data/
├── raw/            # Original Reddit data files
├── processed/      # Ingested and initially processed data
├── cleaned/        # Cleaned and filtered data
└── analyzed/       # Results from various analysis jobs
    ├── sentiment/  # Sentiment analysis results
    ├── keywords/   # Keyword extraction results
    ├── events/     # Event correlation results
    └── analytics/  # Batch analytics results
```

## Pipeline Overview

The pipeline consists of the following steps:

1. **Data Ingestion** (`subreddit_ingestion.py`) - Ingests raw Reddit posts and comments
2. **Data Cleaning** (`clean_posts.py`) - Cleans and preprocesses data, removing deleted posts/comments and non-English content
3. **Sentiment Analysis** (`sentiment_analysis.py`) - Performs sentiment analysis on the cleaned data
4. **Keyword Extraction** (`keyword_extraction.py`) - Extracts key terms and topics
5. **Event Correlation** (`event_correlation.py`) - Correlates events across time periods
6. **Batch Analytics** (`batch_analytics.py`) - Runs final statistical analysis on all processed data

## Individual Job Details

### subreddit_ingestion.py

Processes raw Reddit data files and uploads them to MinIO.

```bash
python job_wrapper.py subreddit_ingestion.py --input-dir PATH_TO_RAW --output-dir PATH_TO_PROCESSED
```

### clean_posts.py

Cleans and filters Reddit data, removing deleted content and non-English posts/comments.

```bash
python job_wrapper.py clean_posts.py --input-dir PATH_TO_PROCESSED --output-dir PATH_TO_CLEANED
```

### sentiment_analysis.py

Runs sentiment analysis on cleaned Reddit content.

```bash
python job_wrapper.py sentiment_analysis.py --input-dir PATH_TO_CLEANED --output-dir PATH_TO_ANALYZED
```

### keyword_extraction.py

Extracts key terms and topics from cleaned content.

```bash
python job_wrapper.py keyword_extraction.py --input-dir PATH_TO_CLEANED --output-dir PATH_TO_KEYWORDS
```

### event_correlation.py

Correlates events across time periods.

```bash
python job_wrapper.py event_correlation.py --input-dir PATH_TO_ANALYZED --output-dir PATH_TO_EVENTS
```

### batch_analytics.py

Runs batch analytics on all processed data.

```bash
python job_wrapper.py batch_analytics.py --input-dir PATH_TO_ANALYZED --output-dir PATH_TO_ANALYTICS
```

## Environment Variables

- `S3_ENDPOINT` - MinIO/S3 endpoint URL (default: http://minio:9000)
- `S3_ACCESS_KEY` - MinIO/S3 access key (default: minioadmin)
- `S3_SECRET_KEY` - MinIO/S3 secret key (default: minioadmin)

## Data Format

The pipeline expects two types of Reddit data:

1. **Posts** - Reddit submissions with title, content, author, etc.
2. **Comments** - Comments on Reddit posts with body text, author, etc.

Input format is expected to be JSON files, with typical Reddit data schema. 