# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based LLM screening tool for systematic reviews that automates the screening of academic papers using dual large language models. The tool leverages OpenAI's GPT models to evaluate studies against PICO-TT criteria (Population, Intervention, Comparison, Outcomes, Time Frame, Study Types) for systematic review inclusion/exclusion decisions.

## Core Architecture

### Main Components

- **`app.py`** - Flask web application providing the main user interface
  - Routes for file upload, streaming screening results, conflict resolution
  - SQLAlchemy models: `Project` (screening projects) and `Article` (individual papers)
  - Export functionality (CSV, RIS, BibTeX formats)
  - Template management for PICO configurations

- **`rag.py`** - Core screening pipeline and CLI interface  
  - Dual-LLM screening logic using conservative (gpt-4o-mini) and liberal (gpt-3.5-turbo) models
  - File format parsers: RIS, BibTeX, CSV, TSV, XML, Medline TXT, PMID lists
  - Batch processing with threading support
  - Database integration for project-based screening

- **`real-dual-llm-evaluator.py`** - Legacy evaluation script (minimal content)

### Database Schema

- **Projects**: Store screening configurations and metadata
- **Articles**: Individual papers with screening status (pending, included, excluded, conflict)
- Uses SQLite with SQLAlchemy ORM

### File Format Support

The tool supports multiple academic reference formats:
- RIS files (Reference Manager format)
- BibTeX files
- CSV/TSV files with title/abstract columns
- XML files (PubMed/NLM format)
- Medline TXT format
- PMID lists (fetches from PubMed via Biopython)

## Development Commands

### Environment Setup
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export ENTREZ_EMAIL=your-email@domain.com  # Required for PMID fetching
```

### Running the Application

**Web Interface:**
```bash
python app.py
```
- Runs Flask development server on debug mode
- Access at http://localhost:5000

**CLI Mode:**
```bash
python rag.py <input_file> <output_file> [batch_size] [--verbose]
```
Example: `python rag.py citations.ris results.csv 10 --verbose`

### Database Operations

The application uses SQLite database (`screening_projects.db`) that gets created automatically. No manual database setup required.

## Key Dependencies

- **Flask** - Web framework
- **SQLAlchemy** - Database ORM  
- **OpenAI** - LLM API integration
- **rispy** - RIS file parsing
- **bibtexparser** - BibTeX file parsing
- **lxml** - XML file parsing
- **biopython** - PubMed data fetching

## Configuration Templates

The system supports saving and loading PICO configuration templates in `config_templates/` directory as JSON files.

## Testing & Quality

**Current Status**: No formal testing framework is implemented.

**To run linting/formatting** (not currently configured):
- Consider adding pytest for testing
- Consider adding black/flake8 for code formatting
- No CI/CD pipeline currently exists

## Important File Locations

- **Templates**: `templates/` (HTML templates for web interface)
- **Uploads**: `uploads/` (uploaded reference files)
- **Results**: `results/` (screening output files)  
- **Test Data**: `test_data/` (sample input files for testing)
- **Config Templates**: `config_templates/` (saved PICO configurations)

## Development Notes

- The dual-LLM approach uses two models with different "personalities" (conservative vs liberal) to identify disagreements requiring human review
- Supports batch processing with configurable batch sizes for large datasets
- All LLM interactions require JSON-formatted responses for structured decision-making
- The system handles disagreements by generating detailed conflict reports using GPT-4