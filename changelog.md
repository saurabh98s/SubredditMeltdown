
# Changelog


# Docker Compose Guide for Development

This guide explains how to use Docker Compose to develop and test your Reddit Meltdown Analysis application.

## Getting Started

### Prerequisites

- Docker and Docker Compose installed on your system
- Git for version control
- A code editor (VS Code recommended)

### Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/SubredditMeltdown.git
   cd SubredditMeltdown
   ```

2. Start all services:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - Zookeeper and Kafka for messaging
   - Spark master and worker for data processing
   - MinIO for S3-compatible storage
   - Backend API (FastAPI)
   - Frontend (Next.js)

3. Access the services:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Spark UI: http://localhost:8080
   - MinIO Console: http://localhost:9001 (login with minioadmin/minioadmin)

## Development Workflow

### Making Changes to Frontend Code

1. Edit frontend code in the `frontend/` directory. The changes will be automatically reflected due to volume mounting:
   ```bash
   # Example: Edit a component
   nano frontend/src/components/SentimentChart.tsx
   ```

2. The development server will automatically reload with your changes.

3. If you add new dependencies, you'll need to rebuild the container:
   ```bash
   docker-compose build frontend
   docker-compose up -d frontend
   ```

### Making Changes to Backend Code

1. Edit backend code in the `backend/` directory:
   ```bash
   # Example: Edit the API
   nano backend/api/main.py
   ```

2. The FastAPI server has auto-reload enabled, so changes will be applied automatically.

3. If you add new dependencies to `requirements.txt`, rebuild the backend:
   ```bash
   docker-compose build backend
   docker-compose up -d backend
   ```

### Working with PySpark Jobs

1. Edit PySpark jobs in the `pyspark_jobs/` directory:
   ```bash
   # Example: Edit sentiment analysis job
   nano pyspark_jobs/sentiment_analysis.py
   ```

2. Submit jobs to Spark:
   ```bash
   docker-compose exec spark-master spark-submit /opt/bitnami/spark/jobs/sentiment_analysis.py --help
   ```

### Testing Data Processing Pipeline

Run the complete data processing pipeline:

```bash
docker-compose exec backend bash
cd /app
bash infra/run_pipeline.sh
```

## Troubleshooting

### Viewing Logs

View logs for a specific service:
```bash
docker-compose logs frontend
docker-compose logs backend
docker-compose logs spark-master
```

Follow logs in real-time:
```bash
docker-compose logs -f frontend
```

### Restarting Services

Restart a specific service:
```bash
docker-compose restart frontend
```

### Rebuilding After Major Changes

If you've made significant changes:
```bash
docker-compose down
docker-compose up --build -d
```

### Checking Container Status

```bash
docker-compose ps
```

## Clean Up

Stop all containers:
```bash
docker-compose down
```

Remove volumes (will delete all data):
```bash
docker-compose down -v
```

## Best Practices

1. **Test Components Individually**: Test frontend and backend separately before testing the integrated system.

2. **Use Development Mode**: The frontend is configured to run in development mode for easier debugging.

3. **Check API Compatibility**: When modifying the backend API, ensure the frontend API client is updated accordingly.

4. **TypeScript Best Practices**: 
   - Define proper interfaces for all data structures
   - Avoid using `any` type
   - Use proper type declarations for third-party libraries

5. **Code Organization**: Keep related components and utilities together in appropriate directories.
