from flask import Flask,jsonify
from config import Config,mongo
from routes.file_routes import file_bp
from services.s3_services import start_health_monitoring,bucket_health
from prometheus_client import start_http_server
from flask_cors import CORS
import utils.metrics


def start_metrics_server(port = 8000):
    start_http_server(port)
    print(f"Prometheus metrics exposed on :{port}/metrics")
    utils.metrics.initialize_metrics()
    
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app,origins="http://localhost:5173",expose_headers=["Content-Disposition"])
    mongo.init_app(app)
    print(mongo.db.list_collection_names())
    from routes import auth
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(file_bp)

    return app

if __name__ == "__main__":
    start_metrics_server(8000)
    app = create_app()
    start_health_monitoring()
    app.run(debug=True)
    @app.route('/health')
    def get_health_status():
        return jsonify(bucket_health)