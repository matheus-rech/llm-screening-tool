import pytest
from unittest.mock import patch, mock_open, MagicMock
from rag import (
    parse_ris_file, parse_bibtex_file, parse_csv_file,
    extract_pmids, fetch_articles_from_pmids, screen_article
)

class TestFileParsers:
    """Test file parsing functions."""
    
    def test_parse_ris_file(self, temp_file, sample_ris_content):
        """Test RIS file parsing."""
        with open(temp_file, 'w') as f:
            f.write(sample_ris_content)
        
        articles = parse_ris_file(temp_file)
        assert len(articles) == 1
        assert articles[0]['title'] == 'Test Article'
        assert articles[0]['abstract'] == 'This is a test abstract for screening.'
    
    def test_parse_csv_file(self, temp_file):
        """Test CSV file parsing."""
        csv_content = "title,abstract\nTest Title,Test Abstract\n"
        with open(temp_file, 'w') as f:
            f.write(csv_content)
        
        articles = parse_csv_file(temp_file)
        assert len(articles) == 1
        assert articles[0]['title'] == 'Test Title'
        assert articles[0]['abstract'] == 'Test Abstract'
    
    def test_extract_pmids(self):
        """Test PMID extraction from text."""
        text_with_pmids = "12345678\n87654321\nNot a PMID\n11111111"
        pmids = extract_pmids(text_with_pmids)
        assert len(pmids) == 3
        assert '12345678' in pmids
        assert '87654321' in pmids
        assert '11111111' in pmids

class TestScreening:
    """Test article screening functions."""
    
    @patch('rag.openai.ChatCompletion.create')
    def test_screen_article_success(self, mock_openai):
        """Test successful article screening."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {'content': '{"decision": "include", "reasoning": "Meets criteria"}'}
        mock_openai.return_value = mock_response
        
        article = {
            'title': 'Test Article',
            'abstract': 'Test abstract about diabetes and exercise'
        }
        
        pico_criteria = {
            'population': 'Adults with diabetes',
            'intervention': 'Exercise',
            'comparison': 'Control',
            'outcomes': 'Blood glucose',
            'time_frame': '6 months',
            'study_types': 'RCT'
        }
        
        result = screen_article(article, pico_criteria, 'gpt-3.5-turbo')
        assert result['decision'] == 'include'
        assert 'reasoning' in result
    
    @patch('rag.openai.ChatCompletion.create')
    def test_screen_article_api_error(self, mock_openai):
        """Test handling of OpenAI API errors."""
        mock_openai.side_effect = Exception("API Error")
        
        article = {'title': 'Test', 'abstract': 'Test'}
        pico_criteria = {'population': 'Test'}
        
        result = screen_article(article, pico_criteria, 'gpt-3.5-turbo')
        assert result['decision'] == 'error'
        assert 'API Error' in result['reasoning']