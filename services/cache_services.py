import json
from config import redis_client, CACHE_TTL, COUNT_TTL, HOT_THRESHOLD

def increment_download_count(file_id:str, region:str) -> int:
    key = f"download_count:{file_id}:{region}"
    
    count = redis_client.incr(key)
    
    if count == 1:
        redis_client.expire(key, COUNT_TTL)
        
    return count

def get_cached_chunk_urls(file_id:str, region:str):
    key = f"chunk_urls_cache:{file_id}:{region}"
    raw = redis_client.get(key)
    return json.loads(raw) if raw else None

def cache_chunk_urls(file_id: str, region: str, chunk_urls: list):
    key = f"chunk_urls_cache:{file_id}:{region}"
    redis_client.setex(key, CACHE_TTL, json.dumps(chunk_urls))
    
def increment_cache_hit(file_id: str, region: str) -> int:
    key = f"cache_hits:{file_id}:{region}"
    hits = redis_client.incr(key)
    if hits == 1:
        redis_client.expire(key, COUNT_TTL)
    return hits

def increment_cache_miss(file_id: str, region: str) -> int:
    key = f"cache_misses:{file_id}:{region}"
    misses = redis_client.incr(key)
    if misses == 1:
        redis_client.expire(key, COUNT_TTL)
    return misses