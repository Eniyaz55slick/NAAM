import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from models import db
from database import init_database
from routes import api
import os

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend
    CORS(app, 
     supports_credentials=True,
     origins=["*"],  # Allow all for now
     allow_headers=["Content-Type"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
   
    
    # Initialize database
    db.init_app(app)
    
    # Initialize mail
    from utils import mail
    mail.init_app(app)
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Initialize database tables
    with app.app_context():
        init_database(app)
    
    # Health check route
    @app.route('/')
    def index():
        return jsonify({
            'message': 'NAAM Farm Animal Tracker API',
            'status': 'running',
            'version': '1.0.0'
        })
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print("="*50)
    print("🐄 NAAM Backend Server Starting...")
    print("="*50)
    print("🌐 Server: http://localhost:5000")
    print("🔌 API: http://localhost:5000/api")
    print("="*50)
    app.run(debug=debug, host='0.0.0.0', port=port)

# Create app for gunicorn
app = create_app()