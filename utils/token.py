import jwt
from datetime import datetime, timedelta
from flask import request, jsonify
from functools import wraps
from flask import current_app
from config import Config

def generate_jwt_token(user_id):
    # Access the JWT_SECRET_KEY from Flask's current app config
    secret_key = current_app.config['JWT_SECRET_KEY']
    
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)  # Token expiration time
    }
    
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token

def validate_jwt_token(token):
    try:
        secret_key = current_app.config['JWT_SECRET_KEY']
        decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
        return decoded
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'token is missing !'}),403
        try:
            data = jwt.decode(token,Config.JWT_SECRET_KEY,algorithms=['HS256'])
            request.user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify ({'message': 'Token has expired !'}),403
        except jwt.InvalidTokenError:
            return jsonify({'message' : 'Invalid Token !'}),403
            
        return f(*args, **kwargs)
        
    return decorated