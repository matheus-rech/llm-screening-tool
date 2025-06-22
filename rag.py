import os
import sys
import csv
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import bibtexparser  # type: ignore
from app import db, Project, Article, app # Import db, models, and app
import uuid
from Bio import Entrez, Medline  # type: ignore
from datetime import datetime
import io

# --- Dependency checks ---
try:
    import rispy
except ImportError:
    print("Error: The 'rispy' package is required. Install it with 'pip install rispy'.")
    sys.exit(1)
try:
    import openai
    from openai import OpenAI
except ImportError:
    print("Error: The 'openai' package is required. Install it with 'pip install openai'.")
    sys.exit(1)
try:
    import bibtexparser  # type: ignore
except ImportError:
    print("Error: The 'bibtexparser' package is required. Install it with 'pip install bibtexparser'.")
    sys.exit(1)
try:
    from lxml import etree  # type: ignore
except ImportError:
    print("Error: The 'lxml' package is required. Install it with 'pip install lxml'.")
    sys.exit(1)
try:
    from Bio import Entrez, Medline  # type: ignore
except ImportError:
    print("Error: The 'biopython' package is required. Install it with 'pip install biopython'.")
    sys.exit(1)

# --- CONFIGURATION ---
CONSERVATIVE_MODEL = "gpt-4o-mini"
LIBERAL_MODEL = "gpt-3.5-turbo" # A faster, potentially less nuanced model
DEFAULT_BATCH_SIZE = 10

# --- Helper Functions (moved to top level) ---

def create_pico_prompt(pico_criteria, study):
    # (Implementation of create_pico_prompt moved here)
    prompt = f"""
    Based on the following PICO criteria, please classify the abstract as "Include", "Exclude", or "Uncertain".
    
    PICO Criteria:
    - Population: {pico_criteria.get('population', 'Not specified')}
    - Intervention: {pico_criteria.get('intervention', 'Not specified')}
    - Comparison: {pico_criteria.get('comparison', 'Not specified')}
    - Outcome: {pico_criteria.get('outcome', 'Not specified')}
    - Timeframe: {pico_criteria.get('timeframe', 'Not specified')}
    - Study Type: {pico_criteria.get('study_type', 'Not specified')}
    
    Abstract to analyze:
    - Title: {study['title']}
    - Abstract: {study['abstract']}
    """
    return prompt

def get_insights(study, config, client, conservative_model, liberal_model):
    # This function now only contains the logic to call the LLMs
    # and parse their responses.
    
    pico_prompt = create_pico_prompt(config["pico"], study)

    try:
        conservative_response_future = client.chat.completions.create(
            model=conservative_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a meticulous assistant for systematic reviews. Analyze the following abstract based on the provided PICO criteria. Your response must be in JSON format with 'decision' (Include/Exclude/Uncertain) and 'reasoning' fields."},
                {"role": "user", "content": pico_prompt}
            ]
        )
        liberal_response_future = client.chat.completions.create(
            model=liberal_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a helpful assistant for systematic reviews, with a bias towards inclusion. Analyze the following abstract based on the provided PICO criteria. Your response must be in JSON format with 'decision' (Include/Exclude/Uncertain) and 'reasoning' fields."},
                {"role": "user", "content": pico_prompt}
            ]
        )

        conservative_insight = json.loads(conservative_response_future.choices[0].message.content)
        liberal_insight = json.loads(liberal_response_future.choices[0].message.content)

    except json.JSONDecodeError as e:
        # Handle cases where the LLM response is not valid JSON
        return {"decision": "error", "reasoning": f"LLM returned invalid JSON: {e}"}, {"decision": "error", "reasoning": f"LLM returned invalid JSON: {e}"}
    except Exception as e:
        # Handle other API errors
        return {"decision": "error", "reasoning": f"API Error: {e}"}, {"decision": "error", "reasoning": f"API Error: {e}"}


    return conservative_insight, liberal_insight

def handle_disagreement(study, conservative_insight, liberal_insight, client):
    # This function contains the logic for generating the conflict report.
    
    conflict_prompt = f"""
    TWO AI ASSISTANTS DISAGREE ON A STUDY'S INCLUSION. RESOLVE THE CONFLICT.

    STUDY:
    - Title: {study['title']}
    - Abstract: {study['abstract']}

    ASSISTANT 1 (Conservative):
    - Decision: {conservative_insight['decision']}
    - Reasoning: {conservative_insight['reasoning']}

    ASSISTANT 2 (Liberal):
    - Decision: {liberal_insight['decision']}
    - Reasoning: {liberal_insight['reasoning']}

    YOUR TASK:
    Analyze both arguments and provide a final, detailed "Conflict Report" in JSON format. Explain the nuances of the disagreement and why each assistant might have reached its conclusion. The JSON object should have a "conflict_report" field.
    """
    
    try:
        resolver_response = client.chat.completions.create(
            model="gpt-4", # Use a powerful model for resolution
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert meta-analyst. Your role is to resolve disagreements between two AI screeners."},
                {"role": "user", "content": conflict_prompt}
            ]
        )
        conflict_details = json.loads(resolver_response.choices[0].message.content)
    except Exception as e:
        conflict_details = {"conflict_report": f"Failed to generate conflict report: {e}"}

    return {
        'final_decision': 'conflict',
        'conflict_details': conflict_details,
        'conservative': conservative_insight,
        'liberal': liberal_insight
    }

def run_screening_pipeline(project_id: str, verbose: bool = False):
    """
    Runs the screening pipeline for a given project ID.
    Fetches project config and articles from the database.
    Updates article status in the database as it runs.
    """
    project = Project.query.get(project_id)
    if not project:
        yield {"type": "error", "message": f"Project with ID {project_id} not found."}
        return

    config = project.config
    articles = project.articles
    
    api_key = config.get("api_key")
    if not api_key:
        yield {"type": "error", "message": "OpenAI API key is missing."}
        return
    client = OpenAI(api_key=api_key)

    if verbose:
        yield {"type": "log", "message": f"Starting screening for project: {project.name}"}
        yield {"type": "total_studies", "total": len(articles)}

    conservative_model = config.get('conservative_model', 'gpt-4o-mini')
    liberal_model = config.get('liberal_model', 'gpt-3.5-turbo')
    
    batch_size = config.get("batch_size", DEFAULT_BATCH_SIZE)

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        
        for article_rec in batch:
            try:
                # Convert SQLAlchemy model to dict for processing
                study_dict = {
                    "id": article_rec.id, "title": article_rec.title, "abstract": article_rec.abstract
                }

                # Run dual-LLM screening
                conservative_insight, liberal_insight = get_insights(study_dict, config, client, conservative_model, liberal_model)
                
                if conservative_insight['decision'] == liberal_insight['decision']:
                    article_rec.status = conservative_insight['decision']
                    article_rec.decision_reasoning = {
                        'final_decision': article_rec.status,
                        'conservative': conservative_insight,
                        'liberal': liberal_insight
                    }
                    event_type = 'result'
                else:
                    article_rec.status = 'conflict'
                    conflict_details = handle_disagreement(
                        study_dict, conservative_insight, liberal_insight, client
                    )
                    article_rec.decision_reasoning = conflict_details
                    event_type = 'conflict'

                db.session.commit()

                yield {
                    "type": event_type,
                    "data": {
                        "id": article_rec.id,
                        "title": article_rec.title,
                        "abstract": article_rec.abstract,
                        "status": article_rec.status,
                        "reasoning": article_rec.decision_reasoning
                    }
                }
            except Exception as e:
                yield {"type": "log", "message": f"Error on article {article_rec.id}: {e}"}

    yield {"type": "finished"}

# --- UTILS ---
def parse_ris_file(file_path: str) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8') as bibliography_file:
        entries = rispy.load(bibliography_file)
    studies = []
    for entry in entries:
        studies.append({
            "studyid": entry.get("id", ""),
            "title": entry.get("title", ""),
            "abstract": entry.get("abstract", "")
        })
    return studies

def parse_tsv_file(file_path: str) -> List[Dict]:
    studies = []
    with open(file_path, 'r', encoding='utf-8') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            studies.append({
                "studyid": row.get("id", row.get("pmid", "")),
                "title": row.get("title", ""),
                "abstract": row.get("abstract", "")
            })
    return studies

def parse_csv_file(file_path: str) -> List[Dict]:
    studies = []
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            studies.append({
                "studyid": row.get("id", row.get("pmid", "")),
                "title": row.get("title", ""),
                "abstract": row.get("abstract", "")
            })
    return studies

def parse_medline_txt_file(file_path: str) -> List[Dict]:
    # Parse Medline TXT (PubMed) format
    studies = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Split records by double newlines (may need to adjust for some files)
    records = re.split(r'\n\s*\n', content)
    for rec in records:
        pmid = ""
        title = ""
        abstract = ""
        lines = rec.split('\n')
        for line in lines:
            if line.startswith('PMID-'):
                pmid = line.replace('PMID-', '').strip()
            elif line.startswith('TI  -'):
                title = line.replace('TI  -', '').strip()
            elif line.startswith('AB  -'):
                abstract = line.replace('AB  -', '').strip()
            elif line.startswith('      ') and abstract:
                # Continuation of abstract
                abstract += ' ' + line.strip()
        if title or abstract:
            studies.append({
                "studyid": pmid,
                "title": title,
                "abstract": abstract
            })
    return studies

def parse_xml_file(file_path: str) -> List[Dict]:
    """
    Parses XML files from PubMed/NLM or Reference Manager.
    Tries to intelligently find the relevant fields.
    """
    studies = []
    print("--> Attempting to parse XML file...")
    try:
        # Use a more robust parser that can handle larger files and recover from some errors
        parser = etree.XMLParser(recover=True, huge_tree=True)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()

        # Try PubMed/NLM format first (e.g., <PubmedArticleSet>)
        articles = root.xpath('//PubmedArticle | //PubmedBookArticle')

        if articles:
            print(f"--> Found {len(articles)} articles. Parsing as PubMed/NLM XML...")
            for article in articles:
                pmid_node = article.find('.//PMID')
                title_node = article.find('.//ArticleTitle')

                # Join multiple abstract text parts if they exist
                abstract_parts = article.xpath('.//Abstract/AbstractText/text()')
                abstract = ' '.join(abstract_parts).strip() if abstract_parts else ""

                if not abstract: # Fallback for other abstract locations
                    abstract_node = article.find('.//AbstractText')
                    if abstract_node is not None and abstract_node.text:
                        abstract = abstract_node.text.strip()

                authors_nodes = article.xpath('.//AuthorList/Author/LastName/text()')
                initials_nodes = article.xpath('.//AuthorList/Author/Initials/text()')
                authors = ', '.join([f"{l} {i}" for l, i in zip(authors_nodes, initials_nodes)])

                journal_node = article.find('.//Journal/Title')
                journal = journal_node.text if journal_node is not None else ""

                year_node = article.find('.//PubDate/Year')
                year = year_node.text if year_node is not None else ""

                if pmid_node is not None and (title_node is not None or abstract):
                    studies.append({
                        "studyid": pmid_node.text or "",
                        "title": title_node.text if title_node is not None else "",
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                    })
            return studies

        # Fallback for other formats like Reference Manager XML
        print("--> No PubMed articles found. Parsing as generic/Reference Manager XML...")
        records = root.xpath('//record | //ref | //entry') # Common record tags
        if not records:
            records = root # Fallback to direct children of root

        for record in records:
            def get_text(parent, tagnames):
                for tag in tagnames:
                    node = parent.find(f'.//{tag}') # Use .// to search descendants
                    if node is not None and node.text:
                        return node.text.strip()
                return ""

            title = get_text(record, ['title', 'titles/title', 'article-title'])
            abstract = get_text(record, ['abstract', 'notes', 'abstract-text'])

            if title or abstract:
                studies.append({
                    "studyid": get_text(record, ['rec-number', 'uid', 'id']),
                    "title": title,
                    "abstract": abstract,
                    "authors": get_text(record, ['authors/author', 'contributors/author']),
                    "journal": get_text(record, ['journal', 'periodical/full-title']),
                    "year": get_text(record, ['year', 'dates/year'])
                })

    except etree.XMLSyntaxError as e:
        print(f"Error: XML file is malformed. {e}")
    except Exception as e:
        print(f"An unexpected error occurred during XML parsing: {e}")

    return studies

def parse_pmid_file_and_fetch(file_path: str, email: str) -> List[Dict]:
    """
    Reads a list of PubMed IDs (PMIDs) from a file, fetches their details
    from PubMed using Biopython's Entrez, and returns a list of study dictionaries.
    """
    studies = []
    print("--> Reading PMIDs from file...")
    with open(file_path, 'r', encoding='utf-8') as f:
        pmids = [line.strip() for line in f if line.strip().isdigit()]

    if not pmids:
        print("Error: No valid PMIDs found in the file.")
        return []

    print(f"--> Found {len(pmids)} PMIDs. Fetching details from PubMed...")

    Entrez.email = email  # Always tell NCBI who you are
    try:
        # Fetch in batches to be nice to the API
        batch_size = 200
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i+batch_size]
            print(f"--> Fetching batch {i//batch_size + 1}...")
            handle = Entrez.efetch(db="pubmed", id=batch_pmids, rettype="medline", retmode="text")
            # Using Medline.parse from Biopython
            records = Medline.parse(handle)

            for record in records:
                # Extract year from DP (Date of Publication), e.g., '2023 Mar 15'
                year = ""
                if "DP" in record:
                    match = re.search(r'\b(\d{4})\b', record["DP"])
                    if match:
                        year = match.group(1)

                studies.append({
                    "studyid": record.get("PMID", ""),
                    "title": record.get("TI", ""),
                    "abstract": record.get("AB", ""),
                    "authors": ", ".join(record.get("AU", [])),
                    "journal": record.get("JT", ""),
                    "year": year
                })
            print(f"--> Fetched details for {len(studies)}/{len(pmids)} records...")

    except Exception as e:
        print(f"Error fetching data from PubMed: {e}")
        print("Please check your internet connection and make sure your email is valid.")

    return studies

def parse_bibtex_file(file_path: str) -> List[Dict]:
    studies = []
    with open(file_path, 'r', encoding='utf-8') as bibfile:
        bib_database = bibtexparser.load(bibfile)
    for entry in bib_database.entries:
        studies.append({
            "studyid": entry.get("ID", entry.get("id", "")),
            "title": entry.get("title", ""),
            "abstract": entry.get("abstract", ""),
            "authors": entry.get("author", ""),
            "journal": entry.get("journal", ""),
            "year": entry.get("year", "")
        })
    return studies

def detect_file_format(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".ris":
        return "ris"
    elif ext == ".tsv":
        return "tsv"
    elif ext == ".csv":
        return "csv"
    elif ext == ".bib":
        return "bibtex"
    elif ext == ".xml":
        # Basic check for XML declaration
        with open(file_path, 'r', encoding='utf-8') as f:
            if f.read(20).strip().lower().startswith('<?xml'):
                return "xml"
    elif ext == ".txt":
        # Try to distinguish Medline TXT from plain text PMID list
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read a few lines to decide
            lines = [f.readline().strip() for _ in range(10)]
            non_empty_lines = [line for line in lines if line]

            # Heuristic 1: All non-empty lines are just numbers -> PMID list
            if non_empty_lines and all(line.isdigit() for line in non_empty_lines):
                return "pmid_list"

            # Heuristic 2: Medline format tags present
            content_sample = "\n".join(lines)
            if 'PMID-' in content_sample and ('TI  -' in content_sample or 'AB  -' in content_sample):
                return "medline_txt"
        # If heuristics for Medline fail, assume it's a list of PMIDs.
        # This is a more forgiving default for .txt files.
        return "pmid_list"
    # Fallback: check header
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().lower()
        if first_line.startswith('ty  -'):
            return "ris"
        elif '\tid\t' in first_line or '\ttitle\t' in first_line:
            return "tsv"
        elif ',' in first_line and ('id' in first_line or 'title' in first_line):
            return "csv"
        elif 'pmid-' in first_line or 'ti  -' in first_line:
            return "medline_txt"
        elif first_line.startswith('@article') or first_line.startswith('@book'):
            return "bibtex"
        elif first_line.startswith('<?xml'):
            return "xml"
    return "unknown"

def load_studies(file_content: str, filename: str, entrez_email: str = "") -> List[Dict]:
    """
    Loads studies from a file's content string.
    Uses a temporary file to leverage existing parsers.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=os.path.splitext(filename)[1], encoding='utf-8') as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name

    try:
        file_format = detect_file_format(tmp_file_path)
        studies = []
        if file_format == "ris":
            studies = parse_ris_file(tmp_file_path)
        elif file_format == "tsv":
            studies = parse_tsv_file(tmp_file_path)
        elif file_format == "csv":
            studies = parse_csv_file(tmp_file_path)
        elif file_format == "medline_txt":
            studies = parse_medline_txt_file(tmp_file_path)
        elif file_format == "bibtex":
            studies = parse_bibtex_file(tmp_file_path)
        elif file_format == "xml":
            studies = parse_xml_file(tmp_file_path)
        elif file_format == "pmid_list":
            if not entrez_email:
                raise ValueError("An email is required for fetching PubMed data for a PMID list.")
            assert entrez_email is not None
            studies = parse_pmid_file_and_fetch(tmp_file_path, entrez_email)
        else:
            raise ValueError(f"Unsupported or unknown file format: {file_format}")
    finally:
        os.remove(tmp_file_path)

    return studies

def build_screening_prompt(study, pico, inclusion, exclusion, research_question):
    return f"""
You are an expert systematic reviewer. Given the following study title and abstract, and the PICO-TT criteria below, decide if the study should be included or excluded. Provide a detailed reasoning and a confidence score.

Title: {study['title']}
Abstract: {study['abstract']}

PICO-TT Criteria:
Population: {pico['population']}
Intervention: {pico['intervention']}
Comparison: {pico['comparison']}
Outcomes: {pico['outcomes']}
Time Frame: {pico['time_frame']}
Study Types: {pico['study_types']}

Inclusion Criteria: {inclusion}
Exclusion Criteria: {exclusion}
Research Question: {research_question}

Respond in JSON:
{{
  "decision": "include" | "exclude" | "uncertain",
  "confidence": 0-100,
  "reasoning": "...",
  "pico_scores": {{
    "population": 0-100,
    "intervention": 0-100,
    "comparison": 0-100,
    "outcomes": 0-100,
    "time_frame": 0-100,
    "study_types": 0-100
  }}
}}
"""

def screen_study_with_llm(study, config, client: OpenAI, model, verbose=False):
    prompt = build_screening_prompt(
        study,
        config['pico'],
        config['inclusion_criteria'],
        config['exclusion_criteria'],
        config['research_question']
    )
    if verbose:
        print("--- PROMPT FOR LLM ---")
        print(prompt)
        print("----------------------")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        llm_output = response.choices[0].message.content or ""
        if verbose:
            print("--- LLM RESPONSE ---")
            print(llm_output)
            print("--------------------")
        return llm_output
    except Exception as e:
        print(f"An unexpected error occurred during LLM call: {e}")
        return json.dumps({"decision": "error", "reasoning": str(e), "model": model}) # Return valid JSON on error

def export_csv(results, filename):
    """Exports the screening results to a CSV file."""
    flat_results = []
    for r in results:
        screening_info = r.get("screening", {})
        flat_row = {
            "studyid": r.get("studyid", ""),
            "title": r.get("title", ""),
            "abstract": r.get("abstract", ""),
            "authors": r.get("authors", ""),
            "journal": r.get("journal", ""),
            "year": r.get("year", ""),
            "screening_status": screening_info.get("status", "error"),
            "decision": "N/A",
            "confidence": "N/A",
            "reasoning": "N/A",
        }

        if screening_info.get('status') == 'agreement':
            flat_row.update({
                'decision': screening_info.get('decision'),
                'confidence': screening_info.get('confidence'),
                'reasoning': screening_info.get('reasoning')
            })
        elif screening_info.get('status') == 'disagreement':
            model1 = screening_info.get('model1', {})
            model2 = screening_info.get('model2', {})
            flat_row.update({
                'decision': f"{model1.get('name')}: {model1.get('decision')}, {model2.get('name')}: {model2.get('decision')}",
                'confidence': f"{model1.get('name')}: {model1.get('confidence')}, {model2.get('name')}: {model2.get('confidence')}",
                'reasoning': f"{model1.get('name')}: {model1.get('reasoning')} | {model2.get('name')}: {model2.get('reasoning')}"
            })
        else:  # Error case
            flat_row['reasoning'] = screening_info.get('error', 'Unknown error')
        
        flat_results.append(flat_row)

    if not flat_results:
        print("Warning: No results to export.")
        return

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = flat_results[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_results)

def export_bibtex(results, filename):
    """Exports the screening results to a BibTeX file."""
    from bibtexparser.bwriter import BibTexWriter  # type: ignore
    from bibtexparser.bibdatabase import BibDatabase  # type: ignore
    db = BibDatabase()
    db.entries = []
    for r in results:
        screening_info = r.get("screening", {})
        notes = f"Screening Status: {screening_info.get('status')}"
        if screening_info.get('status') == 'agreement':
            notes += f", Decision: {screening_info.get('decision')}"
        elif screening_info.get('status') == 'disagreement':
            notes += ", Decision: Disagreement flagged for review"
        
        entry = {
            "ENTRYTYPE": "article",
            "ID": r.get("studyid", "N/A"),
            "title": r.get("title", ""),
            "abstract": r.get("abstract", ""),
            "note": notes
        }
        if r.get("authors"):
            entry["author"] = r["authors"]
        if r.get("journal"):
            entry["journal"] = r["journal"]
        if r.get("year"):
            entry["year"] = r["year"]
        db.entries.append(entry)

    writer = BibTexWriter()
    with open(filename, 'w', encoding='utf-8') as bibfile:
        bibfile.write(writer.write(db))

def export_ris(results, filename):
    """Exports the screening results to an RIS file."""
    entries = []
    for r in results:
        screening_info = r.get("screening", {})
        notes = f"Screening Status: {screening_info.get('status')}"
        if screening_info.get('status') == 'agreement':
            notes += f", Decision: {screening_info.get('decision')}"
        elif screening_info.get('status') == 'disagreement':
            notes += ", Decision: Disagreement flagged for review"

        entry = {
            'type_of_reference': 'JOUR',  # Default to journal article
            'id': r.get('studyid', ''),
            'title': r.get('title', ''),
            'abstract': r.get('abstract', ''),
            'authors': r.get('authors', '').split(', '),  # rispy expects a list for authors
            'journal_name': r.get('journal', ''),
            'year': r.get('year', ''),
            'notes': notes,
        }
        entries.append(entry)

    with open(filename, 'w', encoding='utf-8') as bibliography_file:
        rispy.dump(entries, bibliography_file)

def export_results(results, filename):
    """Main export function to dispatch to the correct exporter based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".csv":
        export_csv(results, filename)
    elif ext == ".bib":
        export_bibtex(results, filename)
    elif ext == ".ris":
        export_ris(results, filename)
    else:
        print(f"Warning: Unknown export format '{ext}'. Defaulting to CSV.")
        export_csv(results, filename.rsplit('.', 1)[0] + ".csv")
    print(f"\nScreening complete. Results exported to {filename}")

def process_study(study, config, client: OpenAI, verbose=False):
    # Call each model once
    result1 = screen_study_with_llm(study, config, client, model=CONSERVATIVE_MODEL, verbose=verbose)
    result2 = screen_study_with_llm(study, config, client, model=LIBERAL_MODEL, verbose=verbose)
    return handle_disagreement(study, result1, result2, client)

def batch_process(studies, config, client: OpenAI, batch_size=DEFAULT_BATCH_SIZE, verbose=False):
    """
    Processes studies in batches and yields progress and results.
    This is a generator function.
    """
    total = len(studies)
    processed_count = 0
    all_results = []

    for batch_start in range(0, total, batch_size):
        batch = studies[batch_start:batch_start+batch_size]
        yield {"type": "log", "message": f"Processing batch {batch_start//batch_size+1} ({min(batch_start+1, total)}-{min(batch_start+batch_size, total)} of {total})..."}

        with ThreadPoolExecutor() as executor:
            future_to_study = {executor.submit(process_study, study, config, client, verbose): study for study in batch}
            for future in as_completed(future_to_study):
                study = future_to_study[future]
                try:
                    screening_result = future.result()
                except Exception as exc:
                    screening_result = {"status": "error", "error": str(exc), "studyid": study.get("studyid", "")}

                processed_count += 1
                combined_result = {**study, "screening": screening_result}
                all_results.append(combined_result)

                yield {"type": "progress", "count": processed_count, "total": total}
                yield {"type": "result", "data": combined_result}

    yield {"type": "log", "message": f"Finished processing {total} studies."}
    yield {"type": "done", "results": all_results}

# --- MAIN SCRIPT (for CLI usage) ---
def main():
    if len(sys.argv) < 3:
        print("Usage: python rag.py <path_to_config.json> <path_to_references_file>")
        sys.exit(1)

    config_path = sys.argv[1]
    input_filepath = sys.argv[2]
    
    print("--- Starting Command-Line Project Creation ---")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        with open(input_filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        filename = os.path.basename(input_filepath)

        # Use Flask's app context to interact with the database
        with app.app_context():
            # Create a new Project in the database
            project_id = str(uuid.uuid4())
            new_project = Project(
                id=project_id, 
                name=config.get('research_question', f'CLI Project - {filename}'),
                description=f"Project created via CLI on {datetime.now()}",
                config=config
            )
            db.session.add(new_project)
            print(f"Creating new project with ID: {project_id}")

            entrez_email = config.get("pico", {}).get("entrez_email")
            studies = load_studies(file_content, filename, entrez_email or "")
            print(f"Loaded {len(studies)} studies from {filename}.")

            # Add articles to the project in the database
            for study_data in studies:
                article = Article(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=study_data.get('title'),
                    abstract=study_data.get('abstract'),
                    authors='; '.join(study_data.get('authors', [])),
                    year=str(study_data.get('year', '')),
                    journal=study_data.get('journal', '')
                )
                db.session.add(article)

            db.session.commit()
            print(f"Successfully created project and added {len(studies)} articles to the database.")
            print("\nTo start the screening, please run the Celery worker and use the web interface.")

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in config file '{config_path}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        db.session.rollback()

if __name__ == "__main__":
    main()