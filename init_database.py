#!/usr/bin/env python3
"""
Initialize database tables for the LLM Screening Tool.
"""

import os
from app import create_app, db

def init_database():
    """Initialize database tables."""
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        return False
    if not os.environ.get('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable not set")
        return False
    
    app = create_app('development')
    
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
            
            from app.models.screening_models import Project, Article
            projects = Project.query.all()
            articles = Article.query.all()
            
            print(f"📊 Current database state:")
            print(f"   Projects: {len(projects)}")
            print(f"   Articles: {len(articles)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False

if __name__ == "__main__":
    init_database()
