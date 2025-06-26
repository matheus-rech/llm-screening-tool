#!/usr/bin/env python3
"""
Upload real test data to project 3 using the test_upload.ris file.
This demonstrates the fixed upload workflow with real citation data.
"""

import sys
import os
import requests
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.screening_models import db, Article, Project
from datetime import datetime

def upload_test_data_via_api(project_id=3, test_file="test_upload.ris"):
    """Upload test data using the Flask upload API endpoint."""
    print("📤 Uploading Real Test Data via API")
    print("=" * 50)
    print(f"Target Project ID: {project_id}")
    print(f"Test File: {test_file}")
    print()
    
    if not os.path.exists(test_file):
        print(f"❌ Test file {test_file} not found!")
        return False
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 Test File Content Preview:")
    print(f"   File size: {len(content)} characters")
    print(f"   First 200 characters: {content[:200]}...")
    print()
    
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            project = Project.query.get(project_id)
            if not project:
                print(f"❌ Project {project_id} not found!")
                return False
            
            print(f"📋 Target Project: {project.name}")
            print(f"   Description: {project.description}")
            print()
            
            with open(test_file, 'rb') as f:
                file_data = {
                    'file': (f, test_file, 'application/x-research-info-systems'),
                    'database_source': 'Test Database'
                }
                
                print(f"🚀 Uploading {test_file} to project {project_id}...")
                
                response = client.post(
                    f'/project/{project_id}/upload',
                    data=file_data,
                    content_type='multipart/form-data'
                )
                
                print(f"   Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.get_json()
                    print(f"   ✅ Upload successful!")
                    print(f"   📊 Articles uploaded: {response_data.get('articles_count', 'Unknown')}")
                    print(f"   📝 Message: {response_data.get('message', 'No message')}")
                    print(f"   🗄️  Database source: {response_data.get('database_source', 'Unknown')}")
                    
                    articles = Article.query.filter_by(project_id=project_id).all()
                    print(f"\n📄 Articles in Database After Upload ({len(articles)} total):")
                    
                    for i, article in enumerate(articles, 1):
                        print(f"   {i}. ID: {article.id}")
                        print(f"      Title: {article.title}")
                        print(f"      Authors: {article.authors}")
                        print(f"      Journal: {article.journal}")
                        print(f"      Year: {article.year}")
                        print(f"      Status: {article.status}")
                        print(f"      Abstract: {article.abstract[:100]}...")
                        print(f"      DOI: {article.doi}")
                        print(f"      PMID: {article.pmid}")
                        print()
                    
                    return len(articles) > 0
                    
                else:
                    print(f"   ❌ Upload failed!")
                    print(f"   Error: {response.get_data(as_text=True)}")
                    return False

def verify_real_data_uploaded(project_id=3):
    """Verify that real test data was uploaded successfully."""
    print("🔍 Verifying Real Data Upload")
    print("=" * 40)
    
    app = create_app()
    with app.app_context():
        articles = Article.query.filter_by(project_id=project_id).all()
        
        expected_titles = [
            "Test Article for File Upload Verification",
            "Second Test Article for Upload Testing"
        ]
        
        print(f"📊 Articles found: {len(articles)}")
        print(f"📊 Expected articles: {len(expected_titles)}")
        
        real_data_count = 0
        for article in articles:
            if article.title in expected_titles:
                real_data_count += 1
                print(f"✅ Real data found: {article.title}")
            else:
                print(f"⚠️  Unexpected article: {article.title}")
        
        print(f"\n📈 Verification Results:")
        print(f"   Real articles found: {real_data_count}/{len(expected_titles)}")
        print(f"   All articles have 'pending' status: {all(a.status == 'pending' for a in articles)}")
        print(f"   All articles have authors: {all(a.authors for a in articles)}")
        print(f"   All articles have abstracts: {all(a.abstract for a in articles)}")
        
        success = (real_data_count == len(expected_titles) and 
                  len(articles) == len(expected_titles) and
                  all(a.status == 'pending' for a in articles))
        
        if success:
            print(f"✅ Real data upload verification: PASSED")
        else:
            print(f"❌ Real data upload verification: FAILED")
        
        return success

def main():
    """Main function to upload real test data."""
    print("🚀 Real Data Upload Script")
    print("This script uploads real test data to replace the mock data.")
    print()
    
    upload_success = upload_test_data_via_api(project_id=3, test_file="test_upload.ris")
    
    if not upload_success:
        print("\n❌ Upload failed!")
        return False
    
    verify_success = verify_real_data_uploaded(project_id=3)
    
    if verify_success:
        print("\n🎉 Real Data Upload Complete!")
        print("✅ Test data successfully uploaded and verified")
        print("✅ Articles have 'pending' status and are ready for screening")
        print("✅ Next step: Verify screening interface displays real data")
        return True
    else:
        print("\n❌ Real Data Upload Verification Failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
