import bcrypt
import logging
from config import mongo
from bson.objectid import ObjectId
from datetime import datetime,timezone

logging.basicConfig(level=logging.DEBUG)

# Function to get the users collection from the MongoDB instance
def get_users_collection(): 
    try:
        logging.info("Attempting to get MongoDB users collection")
        return mongo.db.users  # Use the mongo instance to access the collection
    except Exception as e:
        logging.error(f"Error accessing users collection: {e}")
        raise RuntimeError("Mongo is not initialized")

def register_user(username, password):
    users_collection = get_users_collection()
    logging.info(f"Registering user: {username}")

    existing_user = users_collection.find_one({"username": username})
        
    if existing_user:
        logging.warning(f"User {username} already exists")
        return {"error": "User already exists"}

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_document = {
        'id' : str(ObjectId()),
        'username' : username,
        'password' : hashed_password,
        'created_at' : datetime.now(timezone.utc)
    }
    result = users_collection.insert_one(user_document)
    print(f"Inserted document ID: {result.inserted_id}")
    
    return {'message': 'Successfully registered user!'}, 201

def authenticate_user(username, password):
    users_collection = get_users_collection()
    
    user = users_collection.find_one({'username': username})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return user
    return None
