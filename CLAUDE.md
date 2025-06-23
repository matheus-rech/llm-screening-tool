# CLAUDE.md

This file provides guidance to Claude Code when working with this LLM screening tool repository.

## Project Overview

This is a Python-based dual-LLM screening tool for systematic reviews that automates academic paper screening using OpenAI and Anthropic models.

## Core Architecture

### Main Components

- **`app/`** - Flask application package
  - **`models/screening_models.py`** - SQLAlchemy models (Project, Article)
  - **`routes/main.py`** - Main routes (dashboard, project management)
  - **`routes/screening.py`** - Screening-specific routes
  - **`services/screening/`** - Dual-LLM screening logic
  - **`services/utils/`** - Utilities (file parsing, cost tracking)
  - **`templates/`** - HTML templates (modern dashboard, screening interface)

- **`run.py`** - Application entry point using factory pattern

### Key Features

- **Dual-LLM Architecture**: OpenAI gpt-4o + Anthropic claude-3.5-sonnet
- **Pydantic Structured Outputs**: Reliable data extraction
- **Agreement Analysis**: Mathematical triggers for human review
- **Cost Tracking**: API usage monitoring
- **Multiple File Formats**: RIS, BibTeX, CSV, XML, PMID support

## Development Commands

### Running the Application

```bash
python run.py
```

### Database Initialization

```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().db.create_all()"
```

### Testing

```bash
pytest
```

## Environment Variables

- **OPENAI_API_KEY**: OpenAI API key for gpt-4o
- **ANTHROPIC_API_KEY**: Anthropic API key for claude-3.5-sonnet  
- **ENTREZ_EMAIL**: Email for PubMed API access (PMID fetching)

## Important Notes

- Uses SQLite database (`instance/screening_projects.db`)
- Modern web interface with AlpineJS and TailwindCSS
- Supports both BATCH and LOOP processing strategies
- Built-in error handling and retry logic
- Comprehensive test coverage in `tests/` directory