"""Main Flask application."""
import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import config
from models import db
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Set up logging
    log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO
    setup_logging(app, log_level)
    logger.info(f"Starting Transfer Pricing Policy Generator in {config_name} mode")
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    logger.info("Database and CORS initialized")
    
    # Request/Response logging middleware
    @app.before_request
    def log_request():
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
            logger.debug(f"Request body: {request.get_json()}")
    
    @app.after_request
    def log_response(response):
        logger.info(f"Response: {request.method} {request.path} - Status {response.status_code}")
        return response
    
    # Register blueprints
    from api.companies import companies_bp
    from api.transactions import transactions_bp
    from api.policies import policies_bp
    
    app.register_blueprint(companies_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(policies_bp)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'Transfer Pricing Policy Generator API',
            'version': '1.0.0'
        }), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'message': 'Transfer Pricing Policy Generator API',
            'version': '1.0.0',
            'endpoints': {
                'companies': '/api/companies',
                'transactions': '/api/transactions',
                'policies': '/api/policies',
                'health': '/health'
            }
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
