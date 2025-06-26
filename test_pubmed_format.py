#!/usr/bin/env python3
"""Test script to process the user's PubMed format citation data file with abstracts."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_pubmed_citation_data():
    """Test processing the user's PubMed format citation data file."""
    file_path = '/home/ubuntu/attachments/c82a1a5e-2810-486a-9529-ede3717eb14d/abstract-Trigeminal-set.txt'
    
    try:
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"File size: {len(content)} characters")
        print(f"File lines: {len(content.splitlines())} lines")
        
        from app.services.utils.file_parser import load_studies
        
        studies = load_studies(content, 'abstract-Trigeminal-set.txt')
        print(f"Successfully parsed {len(studies)} studies")
        
        if studies:
            print(f"\nFirst study details:")
            first_study = studies[0]
            print(f"  Title: {first_study.get('title', 'No title')}")
            print(f"  Authors: {first_study.get('authors', 'No authors')}")
            print(f"  Journal: {first_study.get('journal_name', 'No journal')}")
            print(f"  Year: {first_study.get('year', 'No year')}")
            print(f"  Abstract length: {len(first_study.get('abstract', ''))} characters")
            print(f"  DOI: {first_study.get('doi', 'No DOI')}")
            print(f"  PMID: {first_study.get('pmid', 'No PMID')}")
            
            if first_study.get('abstract'):
                print(f"  Abstract preview: {first_study.get('abstract')[:200]}...")
            
            if len(studies) > 1:
                print(f"\nSecond study title: {studies[1].get('title', 'No title')}")
                print(f"Second study abstract length: {len(studies[1].get('abstract', ''))} characters")
            if len(studies) > 2:
                print(f"Third study title: {studies[2].get('title', 'No title')}")
        
        print(f"\nPubMed format parsing test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error processing PubMed file: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pubmed_citation_data()
    sys.exit(0 if success else 1)
