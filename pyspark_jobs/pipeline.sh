#!/bin/bash
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directory variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/s/WORK/PROJECTS/SubredditMeltdown/data"
RAW_DIR="$DATA_DIR/raw"
PROCESSED_DIR="$DATA_DIR/processed"
CLEANED_DIR="$DATA_DIR/cleaned"
ANALYZED_DIR="$DATA_DIR/analyzed"

# Create necessary directories
mkdir -p "$RAW_DIR" "$PROCESSED_DIR" "$CLEANED_DIR" "$ANALYZED_DIR"

# Function to run a job with proper error handling using spark-submit
run_job() {
  local job_file="$1"
  shift
  local job_args=("$@")
  
  echo -e "${YELLOW}Running job: $(basename "$job_file")${NC}"
  # Convert Windows paths to Docker paths
  docker_job_file=$(echo "$job_file" | sed 's/\/s\//\/host_mnt\/s\//g')
  docker_args=()
  for arg in "${job_args[@]}"; do
    docker_args+=("$(echo "$arg" | sed 's/\/s\//\/host_mnt\/s\//g')")
  done
  
  if docker exec spark-master /opt/bitnami/spark/bin/spark-submit \
     --master spark://6aee4b65a51d:7077 \
     "$docker_job_file" "${docker_args[@]}"; then
    echo -e "${GREEN}✓ Job completed successfully${NC}"
    return 0
  else
    echo -e "${RED}✗ Job failed${NC}"
    return 1
  fi
}

# Main pipeline execution
echo -e "${GREEN}🚀 Starting SubredditMeltdown data pipeline...${NC}"

# Step 1: Ingest data from raw source into MinIO
echo -e "${YELLOW}Step 1: Ingesting reddit posts and comments...${NC}"
run_job "$SCRIPT_DIR/subreddit_ingestion.py" \
  --input-dir "$RAW_DIR" \
  --output-dir "$PROCESSED_DIR" \
  --s3-bucket "mh-trends" \
  --s3-prefix "raw"

# Step 2: Clean and preprocess the data
echo -e "${YELLOW}Step 2: Cleaning and preprocessing data...${NC}"
run_job "$SCRIPT_DIR/clean_posts.py" \
  --input-dir "$PROCESSED_DIR" \
  --output-dir "$CLEANED_DIR" \
  --content-type "all" \
  --upload-to-s3 \
  --s3-bucket "mh-trends" \
  --s3-key-prefix "cleaned"

# Step 3: Run sentiment analysis
echo -e "${YELLOW}Step 3: Performing sentiment analysis...${NC}"
run_job "$SCRIPT_DIR/sentiment_analysis.py" \
  --input-dir "$CLEANED_DIR" \
  --output-dir "$ANALYZED_DIR/sentiment" \
  --upload-to-s3 \
  --s3-bucket "mh-trends" \
  --s3-key-prefix "analyzed/sentiment"

# Step 4: Extract keywords
echo -e "${YELLOW}Step 4: Extracting keywords...${NC}"
run_job "$SCRIPT_DIR/keyword_extraction.py" \
  --input-dir "$CLEANED_DIR" \
  --output-dir "$ANALYZED_DIR/keywords" \
  --upload-to-s3 \
  --s3-bucket "mh-trends" \
  --s3-key-prefix "analyzed/keywords"

# Step 5: Correlate events
echo -e "${YELLOW}Step 5: Correlating events...${NC}"
run_job "$SCRIPT_DIR/event_correlation.py" \
  --input-dir "$ANALYZED_DIR" \
  --output-dir "$ANALYZED_DIR/events" \
  --upload-to-s3 \
  --s3-bucket "mh-trends" \
  --s3-key-prefix "analyzed/events"

# Step 6: Run batch analytics
echo -e "${YELLOW}Step 6: Running batch analytics...${NC}"
run_job "$SCRIPT_DIR/batch_analytics.py" \
  --input-dir "$ANALYZED_DIR" \
  --output-dir "$ANALYZED_DIR/analytics" \
  --upload-to-s3 \
  --s3-bucket "mh-trends" \
  --s3-key-prefix "analyzed/analytics"

echo -e "${GREEN}✅ Pipeline execution completed${NC}" 