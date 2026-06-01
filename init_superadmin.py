#!/usr/bin/env python3
"""
SuperAdmin initialization script for DigitalAgri Advisory System

This script creates a new SuperAdmin (Admin model) with secure password hashing.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from __init__ import create_app, db, bcrypt
from models import Admin

def init_superadmin(name, email, password):
    """Create initial superadmin.

    Args:
        name: Full name of the SuperAdmin
        email: Email address (used for login)
        password: Password (min 6 characters)
    """
    app = create_app()

    with app.app_context():
        # Check if superadmin already exists
        existing = Admin.query.filter_by(email=email).first()
        if existing:
            print(f"SuperAdmin with email {email} already exists!")
            return

        # Create new SuperAdmin
        admin = Admin(
            name=name,
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8')
        )
        db.session.add(admin)
        db.session.commit()
        print(f"✅ SuperAdmin '{name}' created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize a SuperAdmin")
    parser.add_argument("--name", required=True, help="Full name")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Password (min 6 chars)")

    args = parser.parse_args()

    if len(args.password) < 6:
        print("❌ Password must be at least 6 characters!")
        sys.exit(1)

    init_superadmin(args.name, args.email, args.password)