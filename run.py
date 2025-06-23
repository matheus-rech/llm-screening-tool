#!/usr/bin/env python3
"""
Application Entry Point
Runs the Flask application using the factory pattern.
"""

import os
from app import create_app, db

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Run the application
    debug = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5000))
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )