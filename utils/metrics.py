from prometheus_client import Counter, Histogram, Gauge

UPLOAD_LATENCY = Histogram(
    'dfs_upload_chunk_seconds',
    'Time spent uploading each chunk',
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
    labelnames=['region']
)

DOWNLOAD_LATENCY = Histogram(
    'dfs_download_chunk_seconds',
    'Time spent downloading each chunk (with failover)',
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
    labelnames=['region']
)

RECONSTRUCT_LATENCY = Histogram(
    'dfs_reconstruction_seconds',
    'Time to reconstruct missing chunks',
    buckets=[0.01, 0.1, 0.5, 1, 5, 10]
)

UPLOAD_THROUGHPUT = Gauge(
    'dfs_upload_chunk_bytes_per_second',
    'Upload throughput per chunk',
    labelnames=['region']
)

ERROR_COUNT = Counter(
    'dfs_errors_total',
    'Number of errors in DFS operations',
    labelnames=['operation','region']
)

def initialize_metrics():
    """Initialize metrics with default values to ensure they appear in exports"""
    # Define your regions
    regions = ['us-east-1', 'eu-west-1','ap-southeast-1' ]  # Add your actual regions
    
    for region in regions:
        # Initialize histograms with a tiny value to ensure buckets appear
        UPLOAD_LATENCY.labels(region=region).observe(0.000001)
        DOWNLOAD_LATENCY.labels(region=region).observe(0.000001)
        
        # Initialize gauge
        UPLOAD_THROUGHPUT.labels(region=region).set(0)
        
        # Initialize counters with 0
        ERROR_COUNT.labels(operation='upload', region=region).inc(0)
        ERROR_COUNT.labels(operation='download', region=region).inc(0)
    
    # Initialize reconstruction latency
    RECONSTRUCT_LATENCY.observe(0.000001)