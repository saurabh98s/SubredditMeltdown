#!/usr/bin/env python3
import boto3
import pandas as pd
import pyarrow.parquet as pq
from io import BytesIO
import logging
from collections import defaultdict
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataAuditor:
    def __init__(self, endpoint_url="http://localhost:9000", 
                 access_key="minioadmin", 
                 secret_key="minioadmin",
                 bucket="mh-trending-subreddits"):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            verify=False
        )
        self.bucket = bucket
        
    def list_objects(self, prefix):
        """List all objects under a prefix"""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
            
            objects = []
            for page in pages:
                if 'Contents' in page:
                    objects.extend(page['Contents'])
            return objects
        except Exception as e:
            logger.error(f"Error listing objects with prefix {prefix}: {str(e)}")
            return []
            
    def get_parquet_stats(self, key):
        """Get statistics for a parquet file"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            parquet_data = BytesIO(response['Body'].read())
            
            # Read parquet metadata
            parquet_file = pq.ParquetFile(parquet_data)
            num_rows = parquet_file.metadata.num_rows
            
            # Read actual data to verify
            df = pq.read_table(parquet_data).to_pandas()
            actual_rows = len(df)
            
            # Get column info
            columns = df.columns.tolist()
            column_stats = {
                col: {
                    'non_null_count': df[col].count(),
                    'null_count': df[col].isnull().sum(),
                    'unique_count': df[col].nunique()
                } for col in columns
            }
            
            return {
                'metadata_rows': num_rows,
                'actual_rows': actual_rows,
                'columns': columns,
                'column_stats': column_stats,
                'file_size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat()
            }
        except Exception as e:
            logger.error(f"Error reading parquet file {key}: {str(e)}")
            return None

    def audit_pipeline(self):
        """Audit data across pipeline stages"""
        stages = {
            'raw': 'raw/',
            'processed': 'processed/',
            'analytics': 'analytics/'
        }
        
        audit_results = defaultdict(dict)
        
        # Audit each stage
        for stage_name, prefix in stages.items():
            logger.info(f"Auditing {stage_name} stage...")
            objects = self.list_objects(prefix)
            
            if not objects:
                logger.warning(f"No objects found in {stage_name} stage")
                continue
                
            total_size = sum(obj['Size'] for obj in objects)
            
            # Group by subreddit
            subreddit_stats = defaultdict(lambda: {'files': 0, 'size': 0, 'rows': 0})
            
            for obj in objects:
                key = obj['Key']
                size = obj['Size']
                
                # Extract subreddit from path
                parts = key.split('/')
                if len(parts) > 2:
                    subreddit = parts[2]  # Assuming path structure like stage/type/subreddit/...
                else:
                    continue
                    
                subreddit_stats[subreddit]['files'] += 1
                subreddit_stats[subreddit]['size'] += size
                
                # For parquet files, get detailed stats
                if key.endswith('.parquet'):
                    stats = self.get_parquet_stats(key)
                    if stats:
                        subreddit_stats[subreddit]['rows'] += stats['actual_rows']
                        if 'parquet_stats' not in subreddit_stats[subreddit]:
                            subreddit_stats[subreddit]['parquet_stats'] = []
                        subreddit_stats[subreddit]['parquet_stats'].append({
                            'file': key,
                            **stats
                        })
            
            audit_results[stage_name] = {
                'total_files': len(objects),
                'total_size': total_size,
                'subreddits': dict(subreddit_stats)
            }
        
        return audit_results

    def save_audit_results(self, results, filename=None):
        """Save audit results to a file"""
        if filename is None:
            filename = f"data_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        try:
            # Save locally
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Audit results saved to {filename}")
            
            # Upload to MinIO
            s3_key = f"analytics/audits/{filename}"
            self.s3_client.upload_file(filename, self.bucket, s3_key)
            logger.info(f"Audit results uploaded to s3://{self.bucket}/{s3_key}")
            
        except Exception as e:
            logger.error(f"Error saving audit results: {str(e)}")

def main():
    logger.info("Starting data pipeline audit...")
    
    auditor = DataAuditor()
    results = auditor.audit_pipeline()
    
    # Print summary
    for stage, stats in results.items():
        logger.info(f"\n=== {stage.upper()} Stage Summary ===")
        logger.info(f"Total Files: {stats['total_files']}")
        logger.info(f"Total Size: {stats['total_size'] / (1024*1024):.2f} MB")
        
        logger.info("\nBy Subreddit:")
        for subreddit, sub_stats in stats['subreddits'].items():
            logger.info(f"\n{subreddit}:")
            logger.info(f"  Files: {sub_stats['files']}")
            logger.info(f"  Size: {sub_stats['size'] / (1024*1024):.2f} MB")
            logger.info(f"  Rows: {sub_stats['rows']}")
            
            if 'parquet_stats' in sub_stats:
                logger.info("\n  Parquet Files:")
                for pstat in sub_stats['parquet_stats']:
                    logger.info(f"    {pstat['file']}:")
                    logger.info(f"      Rows: {pstat['actual_rows']}")
                    logger.info(f"      Columns: {', '.join(pstat['columns'])}")
                    logger.info("      Column Stats:")
                    for col, cstats in pstat['column_stats'].items():
                        logger.info(f"        {col}:")
                        logger.info(f"          Non-null: {cstats['non_null_count']}")
                        logger.info(f"          Null: {cstats['null_count']}")
                        logger.info(f"          Unique: {cstats['unique_count']}")
    
    # Save results
    auditor.save_audit_results(results)

if __name__ == "__main__":
    main() 