#!/usr/bin/env python3
"""Database initialization script for the environmental monitoring system."""

import os
import sys
from database import db


def init_database():
    """Initialize the database with tables and sample data."""
    try:
        print(f"Using database type: sqlite")
        print(f"Database path: {db.db_path}")

        # Use context manager for database operations
        with db.db_session() as database:
            # Initialize database schema
            print("Initializing database schema...")
            database.initialize_database()

            # Initialize parameters
            print("Initializing parameters...")
            database.initialize_parameters()

            # Populate with sample data
            print("Populating with sample data...")
            # database.populate_sample_data()

            # Display database stats
            count = database.get_reading_count()
            print(f"Database initialization complete!")
            print(f"Total readings in database: {count}")

        return True

    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


def main():
    """Main function for database initialization."""
    print("Environmental Monitoring System - Database Initialization")
    print("=" * 60)

    success = init_database()

    if success:
        print("\n✅ Database initialization completed successfully!")
        print("You can now run the Flask application.")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
