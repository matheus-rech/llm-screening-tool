import pytest
import tempfile
import os
from app import create_app, db
from app.models.screening_models import Project, Article

@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app = create_app('testing')
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    os.unlink(path)

@pytest.fixture
def sample_ris_content():
    """Sample RIS content for testing."""
    return """TY  - JOUR
AU  - Smith, John
TI  - Test Article
JO  - Test Journal
PY  - 2023
AB  - This is a test abstract for screening.
ER  - 

"""

@pytest.fixture
def sample_project(client):
    """Create a sample project for testing."""
    app = create_app('testing')
    with app.app_context():
        project = Project(
            name="Test Project",
            population="Adults with diabetes",
            intervention="Exercise therapy",
            comparison="Standard care",
            outcomes="Blood glucose levels",
            time_frame="6 months",
            study_types="RCT, cohort studies"
        )
        db.session.add(project)
        db.session.commit()
        return project