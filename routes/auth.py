from flask import Blueprint, request, jsonify
from models.user import register_user, authenticate_user
from utils.token import generate_jwt_token
import logging
from config import mongo

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        logging.info("Received request to /register")
        data = request.json
        logging.info(f"Request data: {data}")
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            logging.error("Missing username or password")
            return jsonify({'message': 'Username and password required!'}), 400
        
        logging.info(f"Calling register_user for {username}")
        response = register_user(username, password)
        logging.info(f"User registered: {response}")

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error during registration: {e}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login',methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = authenticate_user(username,password)
    if user:
        token = generate_jwt_token(user['id'])
        return jsonify({'token':token}),200
    else:
        return jsonify({'message' : 'Invalid Credentials'}), 401
    
@auth_bp.route('/test_mongo', methods=['GET'])
def test_mongo():
    users = mongo.db.users.find_one()
    return jsonify({"status": "Mongo is connected", "user": users})