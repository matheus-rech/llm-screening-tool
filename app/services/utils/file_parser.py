import csv
import io
import rispy
import bibtexparser
from lxml import etree
from Bio import Entrez, Medline
from typing import List, Dict

# --- FILE PARSING AND DATA LOADING ---

def parse_ris_file(file_content: str) -> List[Dict]:
    entries = rispy.loads(file_content)
    studies = []
    for entry in entries:
        studies.append({
            "title": entry.get("title", entry.get("primary_title", "")),
            "abstract": entry.get("abstract", ""),
            "authors": entry.get("authors", []),
            "year": entry.get("year", ""),
            "journal_name": entry.get("journal_name", "")
        })
    return studies

def parse_tsv_file(file_content: str) -> List[Dict]:
    studies = []
    file_like_object = io.StringIO(file_content)
    reader = csv.DictReader(file_like_object, delimiter='\t')
    for row in reader:
        studies.append({
            "studyid": row.get("id", row.get("pmid", "")),
            "title": row.get("title", ""),
            "abstract": row.get("abstract", "")
        })
    return studies

def parse_csv_file(file_content: str) -> List[Dict]:
    studies = []
    file_like_object = io.StringIO(file_content)
    reader = csv.DictReader(file_like_object)
    for row in reader:
        studies.append({
            "studyid": row.get("id", row.get("pmid", "")),
            "title": row.get("title", ""),
            "abstract": row.get("abstract", "")
        })
    return studies

def parse_medline_txt_file(file_content: str) -> List[Dict]:
    studies = []
    file_like_object = io.StringIO(file_content)
    records = Medline.parse(file_like_object)
    for record in records:
        studies.append({
            "title": record.get("TI", ""),
            "abstract": record.get("AB", ""),
            "authors": record.get("AU", []),
            "year": record.get("DP", "").split()[0] if "DP" in record else "",
            "journal_name": record.get("JT", "")
        })
    return studies


def parse_xml_file(file_content: str) -> List[Dict]:
    studies = []
    try:
        root = etree.fromstring(file_content.encode('utf-8'))
        def get_text(parent, tagnames):
            for tagname in tagnames:
                element = parent.find(f".//{tagname}")
                if element is not None and element.text:
                    return element.text.strip()
            return ""
        for article_element in root.findall('.//PubmedArticle'):
            title = get_text(article_element, ['ArticleTitle'])
            abstract = get_text(article_element, ['AbstractText'])
            studies.append({'title': title, 'abstract': abstract})
    except etree.XMLSyntaxError as e:
        print(f"Error parsing XML: {e}")
    return studies

def parse_pmid_file_and_fetch(file_content: str, email: str) -> List[Dict]:
    Entrez.email = email
    pmids = [line.strip() for line in file_content.splitlines() if line.strip()]
    if not pmids:
        return []
    
    studies = []
    try:
        handle = Entrez.efetch(db="pubmed", id=pmids, rettype="medline", retmode="text")
        records = Medline.parse(handle)
        for record in records:
            studies.append({
                "title": record.get("TI", ""),
                "abstract": record.get("AB", ""),
                "authors": record.get("AU", []),
                "year": record.get("DP", "").split()[0] if "DP" in record else "",
                "journal_name": record.get("JT", "")
            })
    except Exception as e:
        print(f"An error occurred while fetching from PubMed: {e}")
    return studies

def parse_bibtex_file(file_content: str) -> List[Dict]:
    bib_database = bibtexparser.loads(file_content)
    studies = []
    for entry in bib_database.entries:
        studies.append({
            "title": entry.get("title", ""),
            "abstract": entry.get("abstract", ""),
            "authors": entry.get("author", "").split(" and "),
            "year": entry.get("year", ""),
            "journal_name": entry.get("journal", "")
        })
    return studies


def detect_file_format(filename: str) -> str:
    filename_lower = filename.lower()
    if filename_lower.endswith(".ris"):
        return "ris"
    if filename_lower.endswith(".csv"):
        return "csv"
    if filename_lower.endswith(".tsv"):
        return "tsv"
    if filename_lower.endswith(".xml"):
        return "xml"
    if filename_lower.endswith(".bib"):
        return "bibtex"
    if "pmid" in filename_lower and filename_lower.endswith(".txt"):
        return "pmid_list"
    if filename_lower.endswith(".txt"):
        return "medline"
    return "unknown"


def load_studies(file_content: str, filename: str, entrez_email: str = "") -> List[Dict]:
    """
    Loads studies from a file content string based on the detected format.
    """
    file_format = detect_file_format(filename)

    if file_format == "ris":
        return parse_ris_file(file_content)
    elif file_format == "csv":
        return parse_csv_file(file_content)
    elif file_format == "tsv":
        return parse_tsv_file(file_content)
    elif file_format == "xml":
        return parse_xml_file(file_content)
    elif file_format == "bibtex":
        return parse_bibtex_file(file_content)
    elif file_format == "medline":
        return parse_medline_txt_file(file_content)
    elif file_format == "pmid_list":
        if not entrez_email:
            raise ValueError("Email is required for fetching PubMed data.")
        return parse_pmid_file_and_fetch(file_content, entrez_email)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")

def load_studies_with_source_tracking(file_content: str, filename: str, entrez_email: str = "") -> tuple:
    """
    Load studies and determine source database.
    Returns: (studies, source_database)
    """
    file_format = detect_file_format(filename)
    
    source_database = detect_source_database(filename, file_content)
    
    if file_format == "ris":
        studies = parse_ris_file(file_content)
    elif file_format == "csv":
        studies = parse_csv_file(file_content)
    elif file_format == "tsv":
        studies = parse_tsv_file(file_content)
    elif file_format == "xml":
        studies = parse_xml_file(file_content)
    elif file_format == "bibtex":
        studies = parse_bibtex_file(file_content)
    elif file_format == "medline":
        studies = parse_medline_txt_file(file_content)
    elif file_format == "pmid_list":
        if not entrez_email:
            raise ValueError("Email is required for fetching PubMed data.")
        studies = parse_pmid_file_and_fetch(file_content, entrez_email)
        source_database = "PubMed"  # Override for PMID lists
    else:
        raise ValueError(f"Unsupported file format: {file_format}")
    
    return studies, source_database

def detect_source_database(filename: str, content: str) -> str:
    """Detect source database from filename or content patterns."""
    filename_lower = filename.lower()
    
    if "pubmed" in filename_lower or "medline" in filename_lower:
        return "PubMed"
    elif "scopus" in filename_lower:
        return "Scopus"
    elif "embase" in filename_lower:
        return "Embase"
    elif "webofscience" in filename_lower or "wos" in filename_lower:
        return "Web of Science"
    elif "cochrane" in filename_lower:
        return "Cochrane Library"
    
    if content.startswith("TY  -"):
        if "DB  - PubMed" in content or "DP  -" in content:
            return "PubMed"
        elif "DB  - Scopus" in content:
            return "Scopus"
        elif "DB  - Embase" in content:
            return "Embase"
    
    return "Unknown"  