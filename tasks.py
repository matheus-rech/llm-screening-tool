from celery import Celery
import time
from app import app as flask_app, db, Project, Article  # Import Flask app and db models
from rag import get_insights, handle_disagreement, create_pico_prompt # Keep LLM logic in rag
from openai import OpenAI
import json

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Basic Celery configuration
flask_app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)

celery = make_celery(flask_app)

@celery.task(bind=True)
def run_screening_task(self, project_id: str):
    """
    Celery task to run the screening pipeline for a project.
    """
    project = Project.query.get(project_id)
    if not project:
        self.update_state(state='FAILURE', meta={'status': f'Project with ID {project_id} not found.'})
        return

    config = project.config
    articles = project.articles
    total_articles = len(articles)

    api_key = config.get("api_key")
    if not api_key:
        self.update_state(state='FAILURE', meta={'status': 'OpenAI API key is missing.'})
        return
    
    client = OpenAI(api_key=api_key)
    conservative_model = config.get('conservative_model', 'gpt-4o-mini')
    liberal_model = config.get('liberal_model', 'gpt-3.5-turbo')

    processed_count = 0
    for article_rec in articles:
        try:
            # Skip articles that are not in 'pending' status
            if article_rec.status != 'pending':
                processed_count += 1
                continue

            study_dict = {
                "id": article_rec.id, "title": article_rec.title, "abstract": article_rec.abstract
            }
            
            # Check if abstract is empty or too short
            if not study_dict.get('abstract') or len(study_dict['abstract'].strip()) < 20:
                article_rec.status = 'excluded'
                article_rec.decision_reasoning = {'final_decision': 'excluded', 'reasoning': 'Abstract missing or too short.'}
                db.session.commit()
                processed_count += 1
                self.update_state(state='PROGRESS', meta={'current': processed_count, 'total': total_articles, 'status': f'Screening {article_rec.title[:30]}... (Skipped)'})
                continue

            conservative_insight, liberal_insight = get_insights(study_dict, config, client, conservative_model, liberal_model)
            
            if conservative_insight['decision'] == liberal_insight['decision']:
                article_rec.status = conservative_insight['decision'].lower()
                article_rec.decision_reasoning = {
                    'final_decision': article_rec.status,
                    'conservative': conservative_insight,
                    'liberal': liberal_insight
                }
            else:
                article_rec.status = 'conflict'
                conflict_details = handle_disagreement(
                    study_dict, conservative_insight, liberal_insight, client
                )
                article_rec.decision_reasoning = conflict_details

            db.session.commit()
            processed_count += 1
            # Update task state for progress tracking
            self.update_state(state='PROGRESS', meta={'current': processed_count, 'total': total_articles, 'status': f'Screening {article_rec.title[:30]}...'})

        except Exception as e:
            # Log error but continue with other articles
            print(f"Error processing article {article_rec.id}: {e}")
            article_rec.status = 'error' # Mark as error to investigate later
            db.session.commit()
            processed_count += 1
            self.update_state(state='PROGRESS', meta={'current': processed_count, 'total': total_articles, 'status': f'Error on article {article_rec.id}'})


    return {'current': total_articles, 'total': total_articles, 'status': 'Screening complete!', 'result': 42} 