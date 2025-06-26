#!/usr/bin/env python3
"""
Clear mock data from project 3's database to prepare for real uploaded data.
This script removes the sample.ris mock articles that were accidentally loaded.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.screening_models import db, Article, Project, PublicationSource
from datetime import datetime

def clear_mock_data_from_project(project_id=3):
    """Clear all mock articles from the specified project."""
    print("🧹 Clearing Mock Data from Database")
    print("=" * 50)
    print(f"Target Project ID: {project_id}")
    print()
    
    app = create_app()
    with app.app_context():
        project = Project.query.get(project_id)
        if not project:
            print(f"❌ Project {project_id} not found!")
            return False
        
        print(f"📋 Project: {project.name}")
        print(f"   Description: {project.description}")
        print()
        
        articles = Article.query.filter_by(project_id=project_id).all()
        print(f"📄 Current Articles in Database ({len(articles)} total):")
        
        mock_titles = [
            "The effect of exercise on depression in adults",
            "Cognitive behavioral therapy for anxiety in children", 
            "The impact of diet on cardiovascular health: a cohort study"
        ]
        
        mock_articles_found = 0
        for i, article in enumerate(articles, 1):
            print(f"   {i}. ID: {article.id}")
            print(f"      Title: {article.title}")
            print(f"      Authors: {article.authors}")
            print(f"      Status: {article.status}")
            print(f"      Created: {article.created_at}")
            
            if article.title in mock_titles:
                print(f"      🎭 MOCK DATA DETECTED")
                mock_articles_found += 1
            else:
                print(f"      ✅ Real data")
            print()
        
        print(f"🎭 Mock articles detected: {mock_articles_found}/{len(articles)}")
        
        if mock_articles_found == 0:
            print("✅ No mock data found - database is already clean!")
            return True
        
        print(f"\n🗑️  Deleting all {len(articles)} articles from project {project_id}...")
        
        for article in articles:
            pub_sources = PublicationSource.query.filter_by(article_id=article.id).all()
            for pub_source in pub_sources:
                db.session.delete(pub_source)
                print(f"   Deleted publication source for article {article.id}")
        
        deleted_count = 0
        for article in articles:
            print(f"   Deleting article {article.id}: {article.title[:50]}...")
            db.session.delete(article)
            deleted_count += 1
        
        project.total_articles = 0
        project.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            print(f"\n✅ Successfully deleted {deleted_count} articles from project {project_id}")
            print("✅ Database is now clean and ready for real data")
            
            remaining_articles = Article.query.filter_by(project_id=project_id).count()
            print(f"✅ Verification: {remaining_articles} articles remaining in project {project_id}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during deletion: {e}")
            db.session.rollback()
            return False

def main():
    """Main function to clear mock data."""
    print("🚀 Mock Data Cleanup Script")
    print("This script will clear mock data from project 3 to prepare for real uploaded data.")
    print()
    
    success = clear_mock_data_from_project(project_id=3)
    
    if success:
        print("\n🎉 Mock Data Cleanup Complete!")
        print("✅ Database is ready for real uploaded citations")
        print("✅ Next step: Upload real test data using test_upload.ris")
        return True
    else:
        print("\n❌ Mock Data Cleanup Failed!")
        print("❌ Please check the error messages above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
