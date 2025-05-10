#!/usr/bin/env python
# simple_migration.py - Add parent_id column to posts table (simplified)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize database
db = SQLAlchemy(app)

def run_migration():
    """Add parent_id column to posts table"""
    with app.app_context():
        try:
            # Using text() function to wrap the SQL statement
            sql = text("ALTER TABLE posts ADD COLUMN parent_id INTEGER")
            db.session.execute(sql)
            db.session.commit()
            print("Migration completed successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")
            print("Trying alternative approach...")
            
            try:
                # Alternative approach for SQLite
                statements = [
                    text("CREATE TABLE posts_new (id INTEGER PRIMARY KEY, content TEXT NOT NULL, created_at DATETIME NOT NULL, user_id INTEGER NOT NULL, parent_id INTEGER)"),
                    text("INSERT INTO posts_new (id, content, created_at, user_id) SELECT id, content, created_at, user_id FROM posts"),
                    text("DROP TABLE posts"),
                    text("ALTER TABLE posts_new RENAME TO posts")
                ]
                
                for statement in statements:
                    db.session.execute(statement)
                
                db.session.commit()
                print("Migration completed successfully using alternative approach!")
            except Exception as e2:
                db.session.rollback()
                print(f"Error during alternative migration: {e2}")

if __name__ == "__main__":
    run_migration()