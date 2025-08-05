import os
from flask_pymongo import PyMongo
from pymongo import MongoClient
from services.encryption import decrypt_jwt_secret
from redis import Redis

class Config:
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS = os.getenv('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET_NAME = {
    'us-east-1': 'finals-project',
    'us-west-1': 'finals-project-1',
    'ap-southeast-1': 'finals-project-2'
    }

    ENCRYPTED_JWT_SECRET_KEY = os.getenv('ENCRYPTED_JWT_SECRET_KEY')
    JWT_SECRET_KEY = decrypt_jwt_secret(ENCRYPTED_JWT_SECRET_KEY)

    MONGO_URI = os.getenv('MONGO_URI')

    CHUNK_SIZE = 5 * 1024 * 1024

mongo = PyMongo()


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses = True)

CACHE_TTL = 60 * 5
COUNT_TTL = 60 * 60 * 24 
HOT_THRESHOLD  = 2 

AWS_REGION_COORDS={
    'us-east-1':     (39.0481, -77.4728),
    'us-west-1':     (37.3382, -121.8863),
    'ap-southeast-1':(1.3521, 103.8198),
}