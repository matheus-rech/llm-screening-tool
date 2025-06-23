"""
Main Application Routes
Contains the primary Flask routes from the original app.py
"""

import json
import os
from datetime import datetime
from io import StringIO
import csv
import logging

import pandas as pd
import rispy
import bibtexparser
from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, Response, stream_with_context, jsonify, send_file
from werkzeug.utils import secure_filename

from app.models.screening_models import db, Project, Article
from app.services.utils.file_parser import load_studies

logger = logging.getLogger(__name__)

# Create Blueprint for main routes
main_bp = Blueprint('main', __name__)

# Ensure directories exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('results', exist_ok=True)
os.makedirs('config_templates', exist_ok=True)

@main_bp.route('/')
def dashboard():
    """Main dashboard showing all projects."""
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    return render_template('dashboard.html', projects=projects)

@main_bp.route('/create_project', methods=['GET', 'POST'])
def create_project():
    """Create a new screening project."""
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        
        project = Project(
            name=name,
            description=description,
            status='active'
        )
        
        db.session.add(project)
        db.session.commit()
        
        return redirect(url_for('main.project_detail', project_id=project.id))
    
    return render_template('create_project.html')

@main_bp.route('/project/<int:project_id>')
def project_detail(project_id):
    """Show project details and articles."""
    project = Project.query.get_or_404(project_id)
    articles = Article.query.filter_by(project_id=project_id).order_by(Article.created_at.desc()).all()
    
    # Calculate statistics
    total_articles = len(articles)
    processed_articles = len([a for a in articles if a.status != 'pending'])
    included_count = len([a for a in articles if a.status == 'included'])
    excluded_count = len([a for a in articles if a.status == 'excluded'])
    
    stats = {
        'total': total_articles,
        'processed': processed_articles,
        'included': included_count,
        'excluded': excluded_count,
        'pending': total_articles - processed_articles
    }
    
    return render_template('dashboard.html', project=project, articles=articles, stats=stats)

@main_bp.route('/project/<int:project_id>/upload', methods=['POST'])
def upload_file(project_id):
    """Upload and parse reference files."""
    project = Project.query.get_or_404(project_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        try:
            # Parse the file
            studies = load_studies(filepath)
            
            # Create articles in database
            articles_created = 0
            for study in studies:
                article = Article(
                    project_id=project_id,
                    title=study.get('title', ''),
                    authors=study.get('authors', ''),
                    journal=study.get('journal', ''),
                    year=study.get('year'),
                    abstract=study.get('abstract', ''),
                    doi=study.get('doi', ''),
                    pmid=study.get('pmid', ''),
                    original_data=study,
                    status='pending'
                )
                db.session.add(article)
                articles_created += 1
            
            # Update project
            project.original_filename = filename
            project.file_path = filepath
            project.total_articles = articles_created
            project.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded and parsed {articles_created} articles',
                'articles_count': articles_created
            })
            
        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}")
            return jsonify({'error': f'Error parsing file: {str(e)}'}), 500

@main_bp.route('/project/<int:project_id>/export/dual-llm-comparison')
def export_dual_llm_comparison(project_id):
    """Export dual-LLM comparison spreadsheet."""
    project = Project.query.get_or_404(project_id)
    articles = Article.query.filter_by(project_id=project_id).all()
    
    articles_with_results = [a for a in articles if a.decision_reasoning]
    
    if not articles_with_results:
        return jsonify({'error': 'No dual-LLM screening results found'}), 400
    
    from app.services.utils.dual_llm_comparison_exporter import DualLLMComparisonExporter
    exporter = DualLLMComparisonExporter()
    
    try:
        filepath = exporter.generate_comparison_spreadsheet(articles_with_results, project.name)
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f'{project.name}_dual_llm_comparison.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error generating comparison spreadsheet: {str(e)}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@main_bp.route('/project/<int:project_id>/export/<format>')
def export_results(project_id, format):
    """Export screening results in various formats."""
    project = Project.query.get_or_404(project_id)
    articles = Article.query.filter_by(project_id=project_id).all()
    
    if format == 'csv':
        return export_csv(project, articles)
    elif format == 'ris':
        return export_ris(project, articles)
    elif format == 'bibtex':
        return export_bibtex(project, articles)
    else:
        return jsonify({'error': 'Unsupported format'}), 400

def export_csv(project, articles):
    """Export results as CSV."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Title', 'Authors', 'Journal', 'Year', 'Abstract', 'DOI', 'PMID', 'Status', 'Decision_Reasoning'])
    
    # Write articles
    for article in articles:
        writer.writerow([
            article.title or '',
            article.authors or '',
            article.journal or '',
            article.year or '',
            article.abstract or '',
            article.doi or '',
            article.pmid or '',
            article.status or '',
            str(article.decision_reasoning) if article.decision_reasoning else ''
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={project.name}_results.csv'}
    )

def export_ris(project, articles):
    """Export results as RIS format."""
    ris_entries = []
    
    for article in articles:
        entry = {
            'TY': 'JOUR',  # Journal article
            'TI': article.title or '',
            'AU': [author.strip() for author in (article.authors or '').split(',') if author.strip()],
            'JO': article.journal or '',
            'PY': str(article.year) if article.year else '',
            'AB': article.abstract or '',
            'DO': article.doi or '',
            'N1': f"Status: {article.status}"
        }
        
        # Remove empty fields
        entry = {k: v for k, v in entry.items() if v}
        ris_entries.append(entry)
    
    # Convert to RIS format
    ris_output = rispy.dumps(ris_entries)
    
    return Response(
        ris_output,
        mimetype='application/x-research-info-systems',
        headers={'Content-Disposition': f'attachment; filename={project.name}_results.ris'}
    )

def export_bibtex(project, articles):
    """Export results as BibTeX format."""
    bib_db = bibtexparser.bibdatabase.BibDatabase()
    
    for i, article in enumerate(articles):
        entry = {
            'ENTRYTYPE': 'article',
            'ID': f'article_{i+1}',
            'title': article.title or '',
            'author': article.authors or '',
            'journal': article.journal or '',
            'year': str(article.year) if article.year else '',
            'abstract': article.abstract or '',
            'doi': article.doi or '',
            'note': f"Status: {article.status}"
        }
        
        # Remove empty fields
        entry = {k: v for k, v in entry.items() if v}
        bib_db.entries.append(entry)
    
    # Convert to BibTeX format
    writer = bibtexparser.bwriter.BibTexWriter()
    bibtex_output = writer.write(bib_db)
    
    return Response(
        bibtex_output,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={project.name}_results.bib'}
    )

@main_bp.route('/project/<int:project_id>/screening')
def screening_interface(project_id):
    """Show the screening interface."""
    project = Project.query.get_or_404(project_id)
    return render_template('screening/modern_screening_interface.html', project=project)

@main_bp.route('/project/<int:project_id>/analytics')
def analytics_dashboard(project_id):
    """Show the analytics dashboard."""
    project = Project.query.get_or_404(project_id)
    return render_template('analytics/analytics_dashboard.html', project=project)

# Legacy routes for compatibility
@main_bp.route('/screening_tool')
def legacy_screening_tool():
    """Legacy screening tool route."""
    return render_template('screening_tool.html')

@main_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory('uploads', filename)

@main_bp.route('/results/<filename>')
def result_file(filename):
    """Serve result files."""
    return send_from_directory('results', filename)
