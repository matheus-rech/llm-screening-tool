#!/usr/bin/env python
"""Database management script for the LLM screening tool."""

import os
import sys
from flask.cli import FlaskGroup
from app import app, db
from flask_migrate import init, migrate, upgrade, downgrade

cli = FlaskGroup(app)

@cli.command("init-db")
def init_db():
    """Initialize the database with migrations support."""
    if not os.path.exists('migrations'):
        init()
        print("Database migration repository initialized.")
    else:
        print("Migration repository already exists.")
    
    # Create initial migration
    migrate(message='Initial migration')
    print("Initial migration created.")
    
    # Apply the migration
    upgrade()
    print("Database initialized and up to date.")

@cli.command("migrate-db")
def migrate_db():
    """Create a new database migration."""
    message = input("Enter migration message (or press Enter for auto-generated): ").strip()
    if not message:
        message = None
    
    migrate(message=message)
    print("Migration created successfully.")

@cli.command("upgrade-db")
def upgrade_db():
    """Apply pending database migrations."""
    upgrade()
    print("Database upgraded successfully.")

@cli.command("downgrade-db")
def downgrade_db():
    """Downgrade database by one migration."""
    if input("Are you sure you want to downgrade? (y/N): ").lower() == 'y':
        downgrade()
        print("Database downgraded successfully.")
    else:
        print("Downgrade cancelled.")

@cli.command("create-tables")
def create_tables():
    """Create all database tables (legacy method)."""
    db.create_all()
    print("All tables created successfully.")

if __name__ == '__main__':
    cli()