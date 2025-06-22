# Production LLM Screening Tool

A professional-grade, AI-powered tool for systematic review screening, inspired by best practices in evidence synthesis and the AIscreenR R package. This tool leverages dual large language models (LLMs) to automate and audit the screening of studies for systematic reviews, with full support for PICO-TT criteria, inclusion/exclusion logic, and transparent disagreement handling.

## Features
- **Dual LLM Screening:** Each study is independently screened by two LLM runs (or models), supporting robust, auditable decisions.
- **PICO-TT Framework:** User-defined Population, Intervention, Comparison, Outcomes, Time Frame, and Study Types.
- **Inclusion/Exclusion Criteria:** Flexible, user-specified criteria for precise screening.
- **Disagreement Handling:** Flags studies where LLMs disagree for human review.
- **Export:** Results are exported to CSV for further analysis or integration with review software.
- **RIS File Support:** Reads standard RIS files for input.

## Installation

1. Clone this repository or download the code.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Obtain an OpenAI API key from https://platform.openai.com/account/api-keys and set it as an environment variable:

```bash
export OPENAI_API_KEY=sk-...
```

## Usage

Run the screening tool from the command line, providing the path to your RIS file:

```bash
python rag.py path/to/your_file.ris
```

You will be prompted to enter your PICO-TT criteria, inclusion/exclusion criteria, and research question. The tool will then process each study, run dual LLM screenings, and export the results to `screening_results.csv`.

## Input Format
- **RIS file**: Standard RIS format as exported from reference managers or databases (e.g., EPPI-Reviewer, EndNote, Zotero).
- Each entry should have at least `ID`, `TI` (title), and `AB` (abstract) fields.

## Output Format
- **CSV file**: `screening_results.csv` with columns for status, decision, confidence, and reasoning. Disagreements are flagged and include both LLM rationales.

## Example Workflow
1. Prepare your RIS file with studies to screen.
2. Set your OpenAI API key.
3. Run the tool and enter your screening criteria when prompted.
4. Review the progress and results in the terminal.
5. Open `screening_results.csv` for a summary of all screening decisions and flagged disagreements.

## Future Directions
- Batch processing and parallelization for large datasets
- Web-based UI for configuration and review
- Advanced export options (RIS, JSON, Google Sheets)
- Integration with systematic review management platforms
- Support for additional LLM providers (Anthropic, local models, etc.)

## Credits & Inspiration
- Inspired by [AIscreenR](https://cran.r-project.org/package=AIscreenR) and systematic review best practices
- Uses [OpenAI](https://platform.openai.com/) for LLM screening
- RIS parsing via [rispy](https://github.com/raivivek/rispy)

---

*This project is a work in progress. Contributions and feedback are welcome!* 