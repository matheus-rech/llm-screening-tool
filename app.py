import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, Response, stream_with_context, jsonify
import os
from werkzeug.utils import secure_filename
from rag import run_screening_pipeline, export_results, load_studies
from typing import Dict, Any
from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import io
import csv
import rispy
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter
from celery.result import AsyncResult

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['CONFIG_TEMPLATE_FOLDER'] = 'config_templates'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///screening_projects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
db = SQLAlchemy(app)

# Must import tasks after app and config are defined
from tasks import celery, run_screening_task

# --- Database Models ---
class Project(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    config = db.Column(db.JSON)
    articles = db.relationship('Article', backref='project', lazy=True, cascade="all, delete-orphan")
    task_id = db.Column(db.String(155), nullable=True) # To store active screening task ID

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)

class Article(db.Model):
    id = db.Column(db.String, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String, nullable=False)
    abstract = db.Column(db.Text, nullable=True)
    authors = db.Column(db.String, nullable=True)
    year = db.Column(db.String, nullable=True)
    journal = db.Column(db.String, nullable=True)
    status = db.Column(db.String, default='pending') # pending, included, excluded, conflict, error
    decision_reasoning = db.Column(db.JSON, nullable=True)

    def __init__(self, **kwargs):
        super(Article, self).__init__(**kwargs)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['CONFIG_TEMPLATE_FOLDER'], exist_ok=True)

@app.route('/')
def dashboard():
    projects = Project.query.order_by(Project.name).all()
    return render_template('dashboard.html', projects=projects)

@app.route('/project/<project_id>')
def project_view(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('screening_tool.html', project=project)

# This will serve the main HTML page
@app.route('/screening')
def index():
    return render_template('screening_tool.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'references_file' not in request.files:
        return 'No file part in the request', 400
    file = request.files['references_file']
    if not file or not file.filename:
        return 'No selected file', 400

    filename = secure_filename(file.filename)
    input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_filepath)

    # We return a simple JSON response. The frontend will handle the redirect/stream.
    return {
        "message": "File uploaded successfully",
        "filename": filename
    }

@app.route('/create_project', methods=['POST'])
def create_project():
    """Creates a new project from uploaded file and config."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({"error": "No selected file"}), 400

        config_str = request.form.get('config')
        if not config_str:
            return jsonify({"error": "Configuration data is missing."}), 400
        config = json.loads(config_str)

        filename = secure_filename(file.filename)
        
        project_id = str(uuid.uuid4())
        new_project = Project(
            id=project_id,
            name=config.get('research_question', 'Untitled Screening Project'),
            description=f"Screening project started on {datetime.utcnow().strftime('%Y-%m-%d')}.",
            config=config
        )
        db.session.add(new_project)

        file_content = file.read().decode('utf-8')
        entrez_email = config.get("pico", {}).get("entrez_email")
        studies = load_studies(file_content, filename, entrez_email or "")

        df = pd.DataFrame(studies)
        original_count = len(df)
        df.drop_duplicates(subset=['title', 'abstract'], inplace=True)
        deduplicated_studies = df.to_dict('records')
        duplicates_found = original_count - len(deduplicated_studies)

        for study_data in deduplicated_studies:
            article = Article(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=study_data.get('title'),
                abstract=study_data.get('abstract'),
                authors='; '.join(study_data.get('authors', [])),
                year=str(study_data.get('year', '')),
                journal=study_data.get('journal_name', '')
            )
            db.session.add(article)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Project created with {len(deduplicated_studies)} articles. {duplicates_found} duplicates removed.",
            "project_id": project_id
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating project: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/project/<project_id>/start_screening', methods=['POST'])
def start_screening(project_id):
    project = Project.query.get_or_404(project_id)
    if project.task_id:
        # Check the status of the existing task
        task_result = AsyncResult(project.task_id, app=celery)
        if task_result.state not in ['SUCCESS', 'FAILURE']:
            return jsonify({'message': 'Screening is already in progress.', 'task_id': project.task_id}), 202

    # Start a new screening task
    task = run_screening_task.delay(project.id)
    project.task_id = task.id  # Store the new task ID
    db.session.commit()
    
    return jsonify({'message': 'Screening has started.', 'task_id': task.id}), 202

@app.route('/project/<project_id>/status')
def project_status(project_id):
    project = Project.query.get_or_404(project_id)
    
    status_counts = db.session.query(
        Article.status, db.func.count(Article.status)
    ).filter_by(project_id=project.id).group_by(Article.status).all()
    
    counts = {status: count for status, count in status_counts}
    total = sum(counts.values())
    
    response = {
        'total': total,
        'included': counts.get('include', 0), # note .lower() in task
        'excluded': counts.get('exclude', 0), # note .lower() in task
        'conflict': counts.get('conflict', 0),
        'pending': counts.get('pending', 0),
        'error': counts.get('error', 0)
    }

    if project.task_id:
        task_result = AsyncResult(project.task_id, app=celery)
        response['task_status'] = task_result.state
        if task_result.state == 'PROGRESS':
            response['task_progress'] = task_result.info
        elif task_result.state == 'SUCCESS':
            response['task_progress'] = {'status': 'Completed!'}
        elif task_result.state == 'FAILURE':
            response['task_progress'] = {'status': 'Task failed.'}

    return jsonify(response)

@app.route('/results/<filename>')
def download_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)

@app.route('/resolve_conflict', methods=['POST'])
def resolve_conflict():
    data = request.json
    if not data:
        return {"status": "error", "message": "Invalid request. JSON body required."}, 400
    
    project_id = data.get('project_id')
    study_id = data.get('study_id')
    decision = data.get('decision')

    if not all([project_id, study_id, decision]):
        return {"status": "error", "message": "Missing 'project_id', 'study_id', or 'decision' in request."}, 400

    article = Article.query.get(study_id)
    if not article or article.project_id != project_id:
        return {"status": "error", "message": "Article not found in this project."}, 404

    article.status = decision.lower()
    db.session.commit()

    return {"status": "success", "message": f"Conflict resolved for study {study_id}. New status: {decision}"}

@app.route('/export/csv/<project_id>')
def export_csv(project_id):
    project = Project.query.get_or_404(project_id)
    articles = Article.query.filter_by(project_id=project.id, status='included').all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Abstract', 'Authors', 'Year', 'Journal', 'Status'])
    for article in articles:
        writer.writerow([article.title, article.abstract, article.authors, article.year, article.journal, article.status])
    
    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition":
                 f"attachment; filename=project_{project_id}_included.csv"})

@app.route('/export/ris/<project_id>')
def export_ris(project_id):
    project = Project.query.get_or_404(project_id)
    articles = Article.query.filter_by(project_id=project.id, status='included').all()
    
    entries = []
    for article in articles:
        entry = {
            'type_of_reference': 'JOUR',
            'title': article.title,
            'abstract': article.abstract,
            'authors': article.authors.split('; ') if article.authors else [],
            'year': article.year,
            'journal_name': article.journal,
            'id': article.id
        }
        entries.append(entry)

    ris_data = rispy.dumps(entries)
    return Response(
        ris_data,
        mimetype="application/x-research-info-systems",
        headers={"Content-disposition":
                 f"attachment; filename=project_{project_id}_included.ris"})

@app.route('/export/bibtex/<project_id>')
def export_bibtex(project_id):
    project = Project.query.get_or_404(project_id)
    articles = Article.query.filter_by(project_id=project.id, status='included').all()

    db = BibDatabase()
    entries = []
    for article in articles:
        entry = {
            'ENTRYTYPE': 'article',
            'ID': article.id,
            'title': article.title,
            'abstract': article.abstract,
            'author': article.authors.replace(';', ' and ') if article.authors else '',
            'year': article.year,
            'journal': article.journal
        }
        entries.append(entry)
    db.entries = entries
    
    writer = BibTexWriter()
    bibtex_data = writer.write(db)

    return Response(
        bibtex_data,
        mimetype="application/x-bibtex",
        headers={"Content-disposition":
                 f"attachment; filename=project_{project_id}_included.bib"})

@app.route('/template', methods=['POST'])
def save_template():
    data = request.json
    if not data:
        return {"status": "error", "message": "Invalid request. JSON body required."}, 400

    template_name = data.get('template_name')
    config = data.get('config')

    if not template_name or not config:
        return {"status": "error", "message": "Missing template_name or config"}, 400

    filename = secure_filename(template_name) + ".json"
    filepath = os.path.join(app.config['CONFIG_TEMPLATE_FOLDER'], filename)

    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2)

    return {"status": "success", "message": f"Template '{template_name}' saved."}

@app.route('/templates', methods=['GET'])
def get_templates():
    templates = []
    for filename in os.listdir(app.config['CONFIG_TEMPLATE_FOLDER']):
        if filename.endswith(".json"):
            templates.append(filename.replace(".json", ""))
    return {"templates": templates}

@app.route('/template/<filename>', methods=['GET'])
def get_template(filename):
    safe_filename = secure_filename(filename) + ".json"
    try:
        return send_from_directory(app.config['CONFIG_TEMPLATE_FOLDER'], safe_filename)
    except FileNotFoundError:
        return {"status": "error", "message": "Template not found"}, 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, threaded=True) 