#!/bin/bash
set -e

#Configuration
DATA_DIR="/data"
RAW_DIR="${DATA_DIR}/raw"
PROCESSED_DIR="${DATA_DIR}/processed"
ANALYTICS_DIR="${DATA_DIR}/analytics"
S3_BUCKET="mh-trends"

#Create directories if they don't exist
mkdir -p ${RAW_DIR}
mkdir -p ${PROCESSED_DIR}
mkdir -p ${ANALYTICS_DIR}/sentiment
mkdir -p ${ANALYTICS_DIR}/keywords
mkdir -p ${ANALYTICS_DIR}/events_correlation

echo "===== Reddit Meltdown Analysis Pipeline ====="
echo "Starting pipeline execution at $(date)"

# Step 1: Download Reddit data if needed
if [ ! "$(ls -A ${RAW_DIR})" ]; then
  echo "Step 1: Downloading Reddit data"
  python /app/data_ingestion/download_arctic_shift.py \
    --start-date 2020-01 \
    --end-date 2022-12 \
    --output-dir ${RAW_DIR}
else
  echo "Step 1: Skipping download - raw data already exists"
fi

# Step 2: Clean and preprocess the data
echo "Step 2: Cleaning and preprocessing data"
spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.driver.memory=4g \
  --conf spark.executor.memory=4g \
  /opt/bitnami/spark/jobs/clean_posts.py \
  --input-dir ${RAW_DIR} \
  --output-dir ${PROCESSED_DIR} \
  --upload-to-s3 \
  --s3-bucket ${S3_BUCKET}

# Step 3: Run sentiment analysis
echo "Step 3: Running sentiment analysis"
spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.driver.memory=4g \
  --conf spark.executor.memory=4g \
  /opt/bitnami/spark/jobs/sentiment_analysis.py \
  --input-dir ${PROCESSED_DIR} \
  --output-dir ${ANALYTICS_DIR}/sentiment \
  --upload-to-s3 \
  --s3-bucket ${S3_BUCKET}

# Step 4: Extract keywords (for multiple timeframes)
echo "Step 4: Extracting keywords"
for timeframe in monthly quarterly yearly all; do
  echo "  - Processing ${timeframe} keywords"
  spark-submit \
    --master spark://spark-master:7077 \
    --conf spark.driver.memory=4g \
    --conf spark.executor.memory=4g \
    /opt/bitnami/spark/jobs/keyword_extraction.py \
    --input-dir ${PROCESSED_DIR} \
    --output-dir ${ANALYTICS_DIR}/keywords/${timeframe} \
    --timeframe ${timeframe} \
    --upload-to-s3 \
    --s3-bucket ${S3_BUCKET}
done

# Step 5: Correlate sentiment with events
echo "Step 5: Correlating sentiment with events"
spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.driver.memory=4g \
  --conf spark.executor.memory=4g \
  /opt/bitnami/spark/jobs/event_correlation.py \
  --sentiment-path ${ANALYTICS_DIR}/sentiment/combined_sentiment \
  --events-path ${DATA_DIR}/events.csv \
  --output-dir ${ANALYTICS_DIR}/events_correlation \
  --upload-to-s3 \
  --s3-bucket ${S3_BUCKET}

echo "Pipeline completed successfully at $(date)"
echo "Data is available in MinIO bucket: ${S3_BUCKET}" 