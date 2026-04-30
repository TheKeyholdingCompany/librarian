#!/usr/bin/env python3

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.extensions import db

def test_database():
    app = create_app()
    with app.app_context():
        try:
            # Test database connection
            db.session.execute(db.text("SELECT 1"))
            print("✓ Database connection successful")

            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)

            tables = inspector.get_table_names()
            print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")

            # Check if favorites table exists
            if 'favorites' in tables:
                print("✓ Favorites table exists")
            else:
                print("✗ Favorites table missing")

            # Check if ratings table exists
            if 'ratings' in tables:
                print("✓ Ratings table exists")
            else:
                print("✗ Ratings table missing")

            # Check if books have photo_filename column
            if 'books' in tables:
                columns = [col['name'] for col in inspector.get_columns('books')]
                if 'photo_filename' in columns:
                    print("✓ Books table has photo_filename column")
                else:
                    print("✗ Books table missing photo_filename column")

            # Check if users have role column
            if 'users' in tables:
                columns = [col['name'] for col in inspector.get_columns('users')]
                if 'role' in columns:
                    print("✓ Users table has role column")
                else:
                    print("✗ Users table missing role column")

            print("✓ Database schema check complete")

        except Exception as e:
            print(f"✗ Database error: {e}")
            return False

    return True

if __name__ == "__main__":
    test_database()