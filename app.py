from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config,mongo
from routes.file_routes import file_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize MongoDB
    mongo.init_app(app)
    print(mongo.db.list_collection_names())
    # Import routes after app is configured to avoid circular imports
    from routes import auth
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(file_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)