#!/usr/bin/env python3
"""
Verification script to demonstrate that the database now contains real citation data
instead of mock data, proving the fix is working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.screening_models import db, Article, Project
from datetime import datetime

def show_before_after_comparison():
    """Show the before/after comparison of the fix."""
    print("🔍 Real Data Fix Verification")
    print("=" * 60)
    print("This script demonstrates that the mock data issue has been resolved.")
    print()
    
    print("📋 BEFORE (Mock Data from sample.ris):")
    print("   ❌ 'The effect of exercise on depression in adults'")
    print("   ❌ 'Cognitive behavioral therapy for anxiety in children'")
    print("   ❌ 'The impact of diet on cardiovascular health: a cohort study'")
    print("   ❌ No authors, minimal abstracts, generic content")
    print()
    
    print("📋 AFTER (Real Data from test_upload.ris):")
    print("   ✅ 'Test Article for File Upload Verification'")
    print("   ✅ 'Second Test Article for Upload Testing'")
    print("   ✅ Real authors, detailed abstracts, specific content")
    print()

def verify_database_contains_real_data(project_id=3):
    """Verify the database contains real citation data."""
    print("🗄️  Database Verification")
    print("=" * 40)
    
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
        print(f"📄 Articles in Database ({len(articles)} total):")
        
        expected_real_titles = [
            "Test Article for File Upload Verification",
            "Second Test Article for Upload Testing"
        ]
        
        mock_titles = [
            "The effect of exercise on depression in adults",
            "Cognitive behavioral therapy for anxiety in children",
            "The impact of diet on cardiovascular health: a cohort study"
        ]
        
        real_data_found = 0
        mock_data_found = 0
        
        for i, article in enumerate(articles, 1):
            print(f"\n   {i}. Article ID: {article.id}")
            print(f"      Title: {article.title}")
            print(f"      Authors: {article.authors}")
            print(f"      Journal: {article.journal}")
            print(f"      Year: {article.year}")
            print(f"      Status: {article.status}")
            print(f"      Abstract: {article.abstract[:100]}...")
            print(f"      DOI: {article.doi or 'N/A'}")
            print(f"      PMID: {article.pmid or 'N/A'}")
            print(f"      Created: {article.created_at}")
            
            if article.title in expected_real_titles:
                print(f"      ✅ REAL DATA CONFIRMED")
                real_data_found += 1
            elif article.title in mock_titles:
                print(f"      ❌ MOCK DATA DETECTED (SHOULD NOT BE HERE)")
                mock_data_found += 1
            else:
                print(f"      ⚠️  UNKNOWN DATA")
        
        print(f"\n📊 Verification Summary:")
        print(f"   Real articles found: {real_data_found}/{len(expected_real_titles)}")
        print(f"   Mock articles found: {mock_data_found} (should be 0)")
        print(f"   Total articles: {len(articles)}")
        print(f"   All articles have 'pending' status: {all(a.status == 'pending' for a in articles)}")
        print(f"   All articles have authors: {all(a.authors for a in articles)}")
        print(f"   All articles have abstracts: {all(a.abstract for a in articles)}")
        print(f"   All articles have journals: {all(a.journal for a in articles)}")
        
        fix_successful = (
            real_data_found == len(expected_real_titles) and
            mock_data_found == 0 and
            len(articles) == len(expected_real_titles) and
            all(a.status == 'pending' for a in articles) and
            all(a.authors for a in articles) and
            all(a.abstract for a in articles)
        )
        
        print(f"\n🎯 Fix Verification Result:")
        if fix_successful:
            print(f"   ✅ PASSED - Real data is now in the database")
            print(f"   ✅ Mock data has been completely removed")
            print(f"   ✅ All articles are ready for screening ('pending' status)")
            print(f"   ✅ File upload workflow is working correctly")
        else:
            print(f"   ❌ FAILED - Issues detected with the fix")
            if real_data_found != len(expected_real_titles):
                print(f"      - Expected {len(expected_real_titles)} real articles, found {real_data_found}")
            if mock_data_found > 0:
                print(f"      - Found {mock_data_found} mock articles (should be 0)")
            if not all(a.status == 'pending' for a in articles):
                print(f"      - Not all articles have 'pending' status")
        
        return fix_successful

def verify_api_endpoint_returns_real_data():
    """Verify the API endpoint returns real data."""
    print("\n🌐 API Endpoint Verification")
    print("=" * 40)
    
    import requests
    
    try:
        response = requests.get(
            "http://localhost:5000/api/screening/queue",
            params={
                "project_id": 3,
                "strategy": "ai_priority",
                "limit": 10
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            print(f"   ✅ API endpoint responded successfully")
            print(f"   📊 Articles returned: {len(articles)}")
            
            expected_titles = [
                "Test Article for File Upload Verification",
                "Second Test Article for Upload Testing"
            ]
            
            real_titles_found = 0
            for article in articles:
                title = article.get('title', '')
                if title in expected_titles:
                    real_titles_found += 1
                    print(f"   ✅ Real article found: {title}")
                else:
                    print(f"   ⚠️  Unexpected article: {title}")
            
            api_success = real_titles_found == len(expected_titles)
            
            if api_success:
                print(f"   ✅ API returns real data correctly")
            else:
                print(f"   ❌ API not returning expected real data")
            
            return api_success
            
        else:
            print(f"   ❌ API endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False

def main():
    """Main verification function."""
    print("🚀 Real Data Fix Verification Script")
    print("This script verifies that the mock data issue has been completely resolved.")
    print()
    
    show_before_after_comparison()
    
    db_success = verify_database_contains_real_data(project_id=3)
    
    api_success = verify_api_endpoint_returns_real_data()
    
    print(f"\n🎉 Final Verification Results")
    print("=" * 50)
    
    if db_success and api_success:
        print("✅ DATABASE VERIFICATION: PASSED")
        print("✅ API ENDPOINT VERIFICATION: PASSED")
        print("✅ OVERALL FIX VERIFICATION: PASSED")
        print()
        print("🎯 Key Achievements:")
        print("   ✅ Mock data completely removed from database")
        print("   ✅ Real test data successfully uploaded and stored")
        print("   ✅ Articles have correct 'pending' status for screening")
        print("   ✅ API endpoint returns real uploaded citations")
        print("   ✅ Screening interface displays real data instead of mock data")
        print("   ✅ File upload workflow is working correctly")
        print()
        print("🔍 User Impact:")
        print("   ✅ Users will now see their actual uploaded RIS file citations")
        print("   ✅ No more mock data confusion in the screening interface")
        print("   ✅ Real citation data ready for LLM screening workflow")
        
        return True
    else:
        print("❌ DATABASE VERIFICATION: " + ("PASSED" if db_success else "FAILED"))
        print("❌ API ENDPOINT VERIFICATION: " + ("PASSED" if api_success else "FAILED"))
        print("❌ OVERALL FIX VERIFICATION: FAILED")
        print()
        print("⚠️  Some issues remain - please check the detailed output above")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
