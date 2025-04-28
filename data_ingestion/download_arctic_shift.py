#!/usr/bin/env python3
import os
import requests
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SUBMISSION_URL_TEMPLATE = "https://files.pushshift.io/reddit/submissions/RS_{year}-{month:02d}.zst"
COMMENT_URL_TEMPLATE = "https://files.pushshift.io/reddit/comments/RC_{year}-{month:02d}.zst"

def download_file(url, output_dir):
    """
    Download a file from the given URL and save it to the output directory.
    Returns a tuple of (success, filename, error_message)
    """
    filename = os.path.basename(url)
    output_path = os.path.join(output_dir, filename)
    
    # Skip if file already exists
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        logger.info(f"File {filename} already exists, skipping download")
        return True, filename, None
    
    try:
        logger.info(f"Downloading {url} to {output_path}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Successfully downloaded {filename}")
        return True, filename, None
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}: {str(e)}")
        return False, filename, str(e)

def download_monthly_data(year, month, output_dir, content_types=None):
    """
    Download Reddit data for a specific year and month.
    content_types can be 'submissions', 'comments', or both.
    """
    if content_types is None:
        content_types = ['submissions', 'comments']
    
    files_to_download = []
    
    if 'submissions' in content_types:
        submission_url = SUBMISSION_URL_TEMPLATE.format(year=year, month=month)
        files_to_download.append(submission_url)
    
    if 'comments' in content_types:
        comment_url = COMMENT_URL_TEMPLATE.format(year=year, month=month)
        files_to_download.append(comment_url)
    
    results = []
    for url in files_to_download:
        success, filename, error = download_file(url, output_dir)
        results.append((success, filename, error))
    
    return results

def download_data_range(start_date, end_date, output_dir, content_types=None, max_workers=4):
    """
    Download Reddit data for a range of dates.
    Dates should be in format 'YYYY-MM'.
    """
    start_year, start_month = map(int, start_date.split('-'))
    end_year, end_month = map(int, end_date.split('-'))
    
    start_date = datetime(start_year, start_month, 1)
    end_date = datetime(end_year, end_month, 1)
    
    current_date = start_date
    tasks = []
    
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        tasks.append((year, month))
        current_date += relativedelta(months=1)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_monthly_data, year, month, output_dir, content_types)
            for year, month in tasks
        ]
        
        for future in futures:
            future.result()

def main():
    parser = argparse.ArgumentParser(description="Download Reddit data from Arctic Shift")
    parser.add_argument(
        "--start-date",
        default="2008-01",
        help="Start date in format YYYY-MM (default: 2008-01)",
    )
    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y-%m"),
        help=f"End date in format YYYY-MM (default: current month)",
    )
    parser.add_argument(
        "--output-dir",
        default="../data/raw",
        help="Directory to save downloaded files (default: ../data/raw)",
    )
    parser.add_argument(
        "--content-types",
        nargs="+",
        choices=["submissions", "comments"],
        default=["submissions", "comments"],
        help="Content types to download (default: both submissions and comments)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of concurrent downloads (default: 4)",
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info(f"Downloading Reddit data from {args.start_date} to {args.end_date}")
    download_data_range(
        args.start_date,
        args.end_date,
        args.output_dir,
        args.content_types,
        args.max_workers,
    )
    logger.info("Download complete!")

if __name__ == "__main__":
    main() 