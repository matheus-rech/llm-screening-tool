"""
Modern LLM Screening API Routes
Flask API endpoints for the modern dual-provider screening system.
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from flask import Blueprint, request, jsonify, render_template, current_app, session
from app.models.screening_models import db, Project, Article
from app.services.screening import (
    DualProviderScreeningOrchestrator,
    ScreeningCriteria,
    HumanReviewTriggers,
    ScreeningResultsStore,
    ScreeningWorkflowOrchestrator,
    WorkflowConfig,
    WorkflowType,
    WorkflowProgress,
    ScreeningWorkflowFactory
)
# from app.services.utils.cost_tracker import cost_tracker  # Temporarily disabled
from app.services.utils.error_handler import handle_file_parsing_error
from app.services.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Create Blueprint for modern screening routes
modern_screening_bp = Blueprint('modern_screening', __name__, url_prefix='/api/screening')

# ============================================================================
# CONFIGURATION AND SETUP ROUTES
# ============================================================================

@modern_screening_bp.route('/setup', methods=['GET'])
def setup_page():
    """Render the modern screening setup page."""
    return render_template('modern_screening_setup.html')

@modern_screening_bp.route('/start', methods=['POST'])
def start_screening():
    """Initialize a new modern screening project."""
    
    data = request.get_json()
    if not data:
        raise ValidationError("No configuration data provided")
    
    # Validate required fields
    required_fields = ['researchQuestion', 'picott', 'inclusionCriteria', 'exclusionCriteria', 'llmConfig']
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Create screening criteria from configuration
    try:
        criteria = ScreeningCriteria(
            research_question=data['researchQuestion'],
            target_population=data['picott'].get('population', ''),
            target_intervention=data['picott'].get('intervention', ''),
            target_comparison=data['picott'].get('comparison', ''),
            target_outcomes=data['picott'].get('outcomes', '').split(',') if data['picott'].get('outcomes') else [],
            target_time_frame=data['picott'].get('timeFrame', ''),
            target_study_types=data['picott'].get('studyTypes', '').split(',') if data['picott'].get('studyTypes') else [],
            inclusion_criteria=data['inclusionCriteria'],
            exclusion_criteria=data['exclusionCriteria']
        )
    except Exception as e:
        raise ValidationError(f"Invalid screening criteria: {str(e)}")
    
    # Create or update project
    project_id = session.get('current_project_id')
    if project_id:
        project = Project.query.get(project_id)
        if project:
            # Update existing project with modern screening config
            project.config = {
                'modern_screening': True,
                'criteria': criteria.__dict__,
                'llm_config': data['llmConfig'],
                'created_at': datetime.now().isoformat()
            }
        else:
            raise ValidationError("Project not found")
    else:
        raise ValidationError("No active project found. Please upload articles first.")
    
    # Store configuration
    db.session.commit()
    
    # Initialize cost tracking
    cost_tracker.start_tracking(str(project_id))
    
    logger.info(f"Modern screening started for project {project_id}")
    
    return jsonify({
        'success': True,
        'project_id': project_id,
        'message': 'Modern screening initialized successfully'
    })

@modern_screening_bp.route('/interface/<project_id>')
def screening_interface(project_id):
    """Render the modern screening interface."""
    
    project = Project.query.get_or_404(project_id)
    
    return render_template('modern_screening_interface.html', project=project)

# ============================================================================
# ARTICLE QUEUE AND MANAGEMENT ROUTES
# ============================================================================

@modern_screening_bp.route('/queue', methods=['GET'])
def get_article_queue():
    """Get prioritized article queue for screening."""
    
    strategy = request.args.get('strategy', 'ai_priority')
    limit = int(request.args.get('limit', 20))
    project_id = request.args.get('project_id')
    
    if not project_id:
        project_id = session.get('current_project_id')
        if not project_id:
            raise ValidationError("No project specified")
    
    # Get articles based on strategy
    query = Article.query.filter_by(project_id=project_id)
    
    if strategy == 'ai_priority':
        # Prioritize uncertain cases and conflicts
        articles = query.filter(
            Article.status.in_(['pending', 'human_review_required', 'uncertain'])
        ).order_by(Article.created_at.desc()).limit(limit).all()
        
    elif strategy == 'high_confidence':
        # Show high-confidence cases first
        articles = query.filter_by(status='pending').order_by(
            Article.created_at.desc()
        ).limit(limit).all()
        
    elif strategy == 'low_confidence':
        # Show uncertain cases
        articles = query.filter(
            Article.status.in_(['uncertain', 'human_review_required'])
        ).limit(limit).all()
        
    elif strategy == 'conflicts':
        # Show only conflicts
        articles = query.filter_by(status='human_review_required').limit(limit).all()
        
    elif strategy == 'random':
        # Random order
        articles = query.filter_by(status='pending').order_by(db.func.random()).limit(limit).all()
        
    else:
        articles = query.filter_by(status='pending').limit(limit).all()
    
    # Format articles for frontend
    article_data = []
    for article in articles:
        article_info = {
            'id': article.id,
            'title': article.title,
            'authors': article.authors,
            'year': article.year,
            'journal': article.journal,
            'abstract': article.abstract,
            'status': article.status,
            'openai_prediction': None,
            'anthropic_prediction': None,
            'confidence': None,
            'requires_human_review': article.status == 'human_review_required'
        }
        
        # Extract AI predictions if available
        if article.decision_reasoning and isinstance(article.decision_reasoning, dict):
            reasoning = article.decision_reasoning
            
            if 'openai_result' in reasoning and reasoning['openai_result']:
                openai_data = reasoning['openai_result']
                article_info['openai_prediction'] = openai_data.get('screening_decision', {}).get('final_decision')
                
            if 'anthropic_result' in reasoning and reasoning['anthropic_result']:
                anthropic_data = reasoning['anthropic_result']
                article_info['anthropic_prediction'] = anthropic_data.get('screening_decision', {}).get('final_decision')
                
            # Calculate average confidence
            if 'openai_result' in reasoning and 'anthropic_result' in reasoning:
                openai_conf = reasoning['openai_result'].get('screening_decision', {}).get('confidence_score', 0)
                anthropic_conf = reasoning['anthropic_result'].get('screening_decision', {}).get('confidence_score', 0)
                article_info['confidence'] = (openai_conf + anthropic_conf) / 2
        
        article_data.append(article_info)
    
    return jsonify({
        'success': True,
        'articles': article_data,
        'strategy': strategy,
        'total_available': query.count()
    })

@modern_screening_bp.route('/analysis/<article_id>', methods=['GET'])
def get_analysis(article_id):
    """Get AI analysis results for a specific article."""
    
    article = Article.query.get_or_404(article_id)
    
    if not article.decision_reasoning:
        # No analysis available - trigger screening
        return jsonify({
            'success': False,
            'message': 'Analysis not available. Article needs to be screened.',
            'analysis': None,
            'agreement': None
        })
    
    reasoning = article.decision_reasoning
    
    return jsonify({
        'success': True,
        'analysis': {
            'openai': reasoning.get('openai_result'),
            'anthropic': reasoning.get('anthropic_result')
        },
        'agreement': reasoning.get('agreement_analysis'),
        'human_review_triggers': reasoning.get('human_review_triggers'),
        'final_decision': reasoning.get('final_decision')
    })

# ============================================================================
# SCREENING EXECUTION ROUTES
# ============================================================================

@modern_screening_bp.route('/process/<article_id>', methods=['POST'])
def process_article(article_id):
    """Process a single article with dual-provider screening."""
    
    article = Article.query.get_or_404(article_id)
    project = Project.query.get_or_404(article.project_id)
    
    # Get screening criteria from project config
    if not project.config or 'criteria' not in project.config:
        raise ValidationError("Project does not have modern screening configuration")
    
    criteria_dict = project.config['criteria']
    criteria = ScreeningCriteria(**criteria_dict)
    
    # Initialize screening orchestrator
    import os
    orchestrator = DualProviderScreeningOrchestrator(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    
    try:
        # Screen with both providers
        results = orchestrator.screen_article_dual_provider(article, criteria, str(project.id))
        
        # Analyze agreement
        agreement_analysis = orchestrator.analyze_provider_agreement(
            results.get('openai'), results.get('anthropic')
        )
        
        # Check human review triggers
        human_review_triggers = HumanReviewTriggers.should_trigger_human_review(
            results.get('openai'), results.get('anthropic')
        )
        
        # Store results
        screening_record = ScreeningResultsStore.store_screening_results(
            article_id,
            str(project.id),
            results.get('openai'),
            results.get('anthropic'),
            agreement_analysis,
            human_review_triggers
        )
        
        logger.info(f"Article {article_id} processed successfully")
        
        return jsonify({
            'success': True,
            'results': {
                'openai': results.get('openai').model_dump() if results.get('openai') else None,
                'anthropic': results.get('anthropic').model_dump() if results.get('anthropic') else None,
                'agreement': agreement_analysis,
                'human_review_triggers': human_review_triggers,
                'final_decision': screening_record.get('final_decision'),
                'requires_human_review': screening_record.get('requires_human_review')
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to process article {article_id}: {str(e)}")
        raise

@modern_screening_bp.route('/decision', methods=['POST'])
def save_human_decision():
    """Save human reviewer decision."""
    
    data = request.get_json()
    
    required_fields = ['article_id', 'decision']
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    article = Article.query.get_or_404(data['article_id'])
    
    # Update article with human decision
    if not article.decision_reasoning:
        article.decision_reasoning = {}
    
    article.decision_reasoning['human_decision'] = {
        'decision': data['decision'],
        'reasoning': data.get('reasoning', ''),
        'send_to_expert': data.get('send_to_expert', False),
        'add_to_training': data.get('add_to_training', False),
        'timestamp': datetime.now().isoformat(),
        'reviewer_id': session.get('user_id', 'anonymous')
    }
    
    # Update article status based on human decision
    if data['decision'] == 'INCLUDE':
        article.status = 'included'
    elif data['decision'] == 'EXCLUDE':
        article.status = 'excluded'
    else:
        article.status = 'uncertain'
    
    db.session.commit()
    
    logger.info(f"Human decision saved for article {data['article_id']}: {data['decision']}")
    
    return jsonify({
        'success': True,
        'message': 'Decision saved successfully'
    })

# ============================================================================
# PROGRESS AND MONITORING ROUTES  
# ============================================================================

@modern_screening_bp.route('/progress', methods=['GET'])
def get_progress():
    """Get screening progress and statistics."""
    
    project_id = request.args.get('project_id')
    if not project_id:
        project_id = session.get('current_project_id')
        if not project_id:
            raise ValidationError("No project specified")
    
    # Get article counts
    total_articles = Article.query.filter_by(project_id=project_id).count()
    
    processed_articles = Article.query.filter_by(project_id=project_id).filter(
        Article.status.in_(['included', 'excluded', 'uncertain', 'human_review_required'])
    ).count()
    
    included_count = Article.query.filter_by(project_id=project_id, status='included').count()
    excluded_count = Article.query.filter_by(project_id=project_id, status='excluded').count()
    uncertain_count = Article.query.filter_by(project_id=project_id, status='uncertain').count()
    conflict_count = Article.query.filter_by(project_id=project_id, status='human_review_required').count()
    
    # Get cost information
    current_costs = cost_tracker.get_current_costs(project_id)
    total_cost = current_costs.get('total_cost', 0.0) if current_costs else 0.0
    
    # Calculate agreement rate
    agreement_rate = 0.0
    if processed_articles > 0:
        agreement_rate = (processed_articles - conflict_count) / processed_articles
    
    # Provider status (simplified - assume healthy)
    provider_status = {
        'openai': True,
        'anthropic': True
    }
    
    return jsonify({
        'success': True,
        'progress': {
            'total': total_articles,
            'processed': processed_articles,
            'included': included_count,
            'excluded': excluded_count,
            'uncertain': uncertain_count,
            'conflicts': conflict_count
        },
        'cost': total_cost,
        'provider_status': provider_status,
        'agreement_rate': agreement_rate
    })

@modern_screening_bp.route('/stats/<project_id>', methods=['GET'])
def get_detailed_stats(project_id):
    """Get detailed statistics for a project."""
    
    project = Project.query.get_or_404(project_id)
    
    # Basic counts
    articles = Article.query.filter_by(project_id=project_id).all()
    
    stats = {
        'total_articles': len(articles),
        'by_status': {},
        'processing_time': 0,
        'cost_breakdown': {},
        'agreement_analysis': {}
    }
    
    # Count by status
    for article in articles:
        status = article.status
        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
    
    # Calculate agreement metrics
    agreement_count = 0
    disagreement_count = 0
    
    for article in articles:
        if article.decision_reasoning and isinstance(article.decision_reasoning, dict):
            agreement_data = article.decision_reasoning.get('agreement_analysis', {})
            if agreement_data.get('agreement'):
                agreement_count += 1
            else:
                disagreement_count += 1
    
    stats['agreement_analysis'] = {
        'agreements': agreement_count,
        'disagreements': disagreement_count,
        'rate': agreement_count / max(agreement_count + disagreement_count, 1)
    }
    
    # Get cost breakdown
    cost_data = cost_tracker.get_current_costs(project_id)
    if cost_data:
        stats['cost_breakdown'] = cost_data
    
    return jsonify({
        'success': True,
        'stats': stats
    })

# ============================================================================
# WORKFLOW EXECUTION ROUTES
# ============================================================================

@modern_screening_bp.route('/workflow/start', methods=['POST'])
def start_workflow():
    """Start automated screening workflow."""
    
    data = request.get_json()
    project_id = data.get('project_id')
    workflow_type = data.get('workflow_type', 'adaptive')
    
    if not project_id:
        project_id = session.get('current_project_id')
        if not project_id:
            raise ValidationError("No project specified")
    
    project = Project.query.get_or_404(project_id)
    
    # Get screening criteria
    if not project.config or 'criteria' not in project.config:
        raise ValidationError("Project does not have modern screening configuration")
    
    criteria_dict = project.config['criteria']
    criteria = ScreeningCriteria(**criteria_dict)
    
    # Create workflow configuration
    workflow_config = WorkflowConfig(
        workflow_type=WorkflowType(workflow_type),
        batch_size=data.get('batch_size', 10),
        max_concurrent=data.get('max_concurrent', 5),
        enable_early_stopping=data.get('enable_early_stopping', True),
        max_budget=data.get('max_budget')
    )
    
    # Start workflow (simplified - in production this would be async)
    import os
    orchestrator = ScreeningWorkflowOrchestrator(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    
    # Store workflow status
    session['active_workflow'] = {
        'project_id': project_id,
        'started_at': datetime.now().isoformat(),
        'workflow_type': workflow_type
    }
    
    logger.info(f"Workflow started for project {project_id} with type {workflow_type}")
    
    return jsonify({
        'success': True,
        'workflow_id': f"{project_id}-{datetime.now().timestamp()}",
        'message': 'Workflow started successfully'
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@modern_screening_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({
        'success': False,
        'error': 'ValidationError',
        'message': str(error)
    }), 400

@modern_screening_bp.errorhandler(Exception)
def handle_general_error(error):
    logger.error(f"Unhandled error in modern screening: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'InternalError',
        'message': 'An internal error occurred'
    }), 500