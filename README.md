# 🚀 Screening Center MVP

**Production-Ready Automated Systematic Review Screening System**

A professional-grade, AI-powered tool for systematic review screening with dual-LLM intelligence. Complete web interface with real-time processing and advanced PICO-TT criteria support.

## 🎯 Quick Start for Demo

```bash
# 1. Set your API keys
export OPENAI_API_KEY="sk-your-openai-key"
export ENTREZ_EMAIL="your-email@domain.com"

# 2. Launch MVP
./START_MVP.sh

# 3. Access system
open http://localhost:8080
```

## ✨ Core Features

✅ **Dual-LLM Screening Engine**
- OpenAI GPT-4o (conservative approach)
- Anthropic Claude-3.5 (liberal approach)
- Structured Pydantic responses for reliability

✅ **Multi-Format File Support**
- RIS files (Reference Manager format)
- BibTeX files
- CSV/TSV with title/abstract columns
- XML (PubMed/NLM format)
- Medline TXT format
- PMID lists (auto-fetch from PubMed)

✅ **Advanced PICO-TT Configuration**
- Population, Intervention, Comparison, Outcomes
- Time Frame, Study Types
- Custom inclusion/exclusion criteria
- Template save/load functionality

✅ **Real-Time Processing**
- Streaming results with progress tracking
- Concurrent processing with rate limiting
- Cost tracking and error handling
- Retry logic for API failures

✅ **Project Management**
- Multiple systematic review projects
- Configuration templates
- History and progress tracking
- Collaborative reviewer support

✅ **Export Capabilities**
- CSV format with detailed reasoning
- RIS format for reference managers
- BibTeX format for LaTeX/academic use
- Comprehensive reporting

## 🏗️ Architecture

```
app/
├── routes/              # Flask API endpoints
│   ├── main.py         # Core project management
│   └── screening.py    # Screening APIs
├── services/
│   ├── screening/      # Dual-LLM screening engine
│   │   ├── dual_llm_screener.py
│   │   ├── modern_llm.py
│   │   └── workflow.py
│   └── utils/          # File parsers, utilities
│       ├── file_parser.py
│       ├── concurrent_processor.py
│       └── cost_tracker.py
├── models/             # SQLAlchemy database models
│   └── screening_models.py
└── templates/          # HTML web interface
    └── screening/
```

## 🔧 Technology Stack

- **Flask** - Web framework with application factory
- **SQLAlchemy** - Database ORM with migrations
- **OpenAI API** - GPT-4o for systematic screening
- **Anthropic API** - Claude-3.5 for comprehensive coverage
- **Pydantic** - Structured response validation
- **rispy** - RIS file parsing
- **bibtexparser** - BibTeX file parsing
- **biopython** - PubMed integration
- **pytest** - Comprehensive testing suite

## 🚀 Development

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python manage.py init-db
python manage.py upgrade-db

# Run tests
pytest

# Development server
python run.py
```

## 📊 Advanced Features

- **Active Learning** - ML-powered article prioritization
- **Collaborative Screening** - Multi-reviewer workflows
- **Analytics Dashboard** - Screening statistics and insights
- **Workflow Orchestration** - Batch, loop, chain, adaptive modes
- **Error Recovery** - Comprehensive error handling with retries

## 🎯 MVP Status: **PRODUCTION READY**

**Ready for tomorrow's demo with full screening pipeline functional!**

---

*Built with modern Flask architecture and enterprise-grade reliability features.*