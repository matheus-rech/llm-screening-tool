# LLM Screening Tool

A Python-based dual-LLM screening tool for systematic reviews that automates the screening of academic papers using OpenAI and Anthropic models.

## Features

- **Dual-LLM Architecture**: Uses both OpenAI (gpt-4o) and Anthropic (claude-3.5-sonnet) for comprehensive screening
- **PICO-TT Extraction**: Automated extraction of Population, Intervention, Comparison, Outcomes, Time Frame, and Study Types
- **Multiple File Formats**: Supports RIS, BibTeX, CSV, TSV, XML, Medline TXT, and PMID lists
- **Real-time Interface**: Modern web interface with live progress tracking
- **Cost Monitoring**: Built-in API cost tracking and optimization
- **Human Review Triggers**: Mathematical formulas to determine when human review is needed

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Environment Variables

```bash
export OPENAI_API_KEY=your-openai-api-key
export ANTHROPIC_API_KEY=your-anthropic-api-key
export ENTREZ_EMAIL=your-email@domain.com  # For PMID fetching
```

### Running the Application

```bash
python run.py
```

Access the application at: http://localhost:5000

## Architecture

### Core Components

- **`app/`** - Main application package
  - **`models/`** - Database models (Projects, Articles)
  - **`routes/`** - Flask routes (main, screening)
  - **`services/`** - Business logic
    - **`screening/`** - Dual-LLM screening logic
    - **`utils/`** - Utilities (file parsing, cost tracking, error handling)
  - **`templates/`** - HTML templates
  - **`static/`** - CSS/JS assets

### Database

- SQLite database with SQLAlchemy ORM
- Automatic table creation on first run
- Project-based organization

### File Format Support

- **RIS files** (Reference Manager format)
- **BibTeX files**
- **CSV/TSV files** with title/abstract columns
- **XML files** (PubMed/NLM format)
- **Medline TXT format**
- **PMID lists** (fetches from PubMed via Biopython)

## Usage

1. **Create Project**: Set up PICO criteria and inclusion/exclusion rules
2. **Upload References**: Support for multiple academic file formats
3. **AI Screening**: Dual-LLM analysis with agreement tracking
4. **Human Review**: Review conflicts and uncertain cases
5. **Export Results**: CSV, RIS, or BibTeX output formats

## Testing

```bash
pytest
```

## License

MIT License