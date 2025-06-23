"""
Database Models for Systematic Review Screening
Contains SQLAlchemy models for projects, articles, and related entities.
"""

from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy

# This will be imported from app/__init__.py
db = SQLAlchemy()

class Project(db.Model):
    """Project model for systematic review projects."""
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Configuration stored as JSON
    config = db.Column(db.JSON)
    
    # Status tracking
    status = db.Column(db.String(50), default='active')  # active, completed, archived
    
    # File information
    original_filename = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    
    # Statistics
    total_articles = db.Column(db.Integer, default=0)
    processed_articles = db.Column(db.Integer, default=0)
    
    # Relationships
    articles = db.relationship('Article', backref='project_ref', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def to_dict(self):
        """Convert project to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'config': self.config,
            'status': self.status,
            'total_articles': self.total_articles,
            'processed_articles': self.processed_articles
        }

class Article(db.Model):
    """Article model for individual research papers."""
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # Article metadata
    title = db.Column(db.Text)
    authors = db.Column(db.Text)
    journal = db.Column(db.String(500))
    year = db.Column(db.Integer)
    abstract = db.Column(db.Text)
    doi = db.Column(db.String(200))
    pmid = db.Column(db.String(50))
    
    # Original citation data (stored as JSON for flexibility)
    original_data = db.Column(db.JSON)
    
    # Screening status
    status = db.Column(db.String(50), default='pending')  # pending, included, excluded, uncertain, human_review_required
    
    # Decision reasoning (stores AI analysis and human decisions)
    decision_reasoning = db.Column(db.JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Screening metadata
    screened_by = db.Column(db.String(100))  # user or AI model identifier
    screening_date = db.Column(db.DateTime)
    
    # Priority score (for active learning)
    priority_score = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<Article {self.title[:50]}...>'
    
    def to_dict(self):
        """Convert article to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'year': self.year,
            'abstract': self.abstract,
            'doi': self.doi,
            'pmid': self.pmid,
            'status': self.status,
            'decision_reasoning': self.decision_reasoning,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'screened_by': self.screened_by,
            'screening_date': self.screening_date.isoformat() if self.screening_date else None,
            'priority_score': self.priority_score
        }

# Additional models for enhanced features

class Reviewer(db.Model):
    """Model for collaborative screening reviewers."""
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    role = db.Column(db.String(50), default='reviewer')  # reviewer, expert, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Reviewer {self.name}>'

class ReviewAssignment(db.Model):
    """Model for tracking reviewer assignments to projects."""
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('reviewer.id'), nullable=False)
    role = db.Column(db.String(50), default='reviewer')  # reviewer, adjudicator, expert
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Performance tracking
    articles_reviewed = db.Column(db.Integer, default=0)
    agreement_rate = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<ReviewAssignment P{self.project_id} R{self.reviewer_id}>'

class ScreeningDecision(db.Model):
    """Model for individual screening decisions (supports multiple reviewers)."""
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('reviewer.id'), nullable=True)  # None for AI decisions
    
    # Decision details
    decision = db.Column(db.String(20), nullable=False)  # INCLUDE, EXCLUDE, UNCERTAIN
    confidence = db.Column(db.Float)
    reasoning = db.Column(db.Text)
    
    # Decision metadata
    decision_type = db.Column(db.String(20), default='human')  # human, ai_openai, ai_anthropic
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional data (stored as JSON)
    decision_metadata = db.Column(db.JSON)
    
    def __repr__(self):
        return f'<ScreeningDecision A{self.article_id} {self.decision}>'

class ConflictResolution(db.Model):
    """Model for tracking conflict resolution between reviewers."""
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    
    # Conflict details
    reviewer1_decision = db.Column(db.String(20))
    reviewer2_decision = db.Column(db.String(20))
    final_decision = db.Column(db.String(20))
    
    # Resolution metadata
    resolved_by = db.Column(db.Integer, db.ForeignKey('reviewer.id'))
    resolution_method = db.Column(db.String(50))  # discussion, adjudication, ai_assistance
    resolution_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<ConflictResolution A{self.article_id}>'