from flask import Flask,jsonify
from config import Config,mongo
from routes.file_routes import file_bp
from services.s3_services import start_health_monitoring,bucket_health

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
    start_health_monitoring()
    app.run(debug=True)
    @app.route('/health')
    def get_health_status():
        return jsonify(bucket_health)