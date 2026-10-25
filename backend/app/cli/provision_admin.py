"""CLI script for securely provisioning administrator and supervisor accounts (Module 12).

Usage:
    python -m app.cli.provision_admin --email admin@example.com --name "System Admin" --role admin
"""

import argparse
import getpass
import sys

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.repositories.user import create_user, get_user_by_email


def provision_user(email: str, password: str, display_name: str | None, role: str) -> None:
    """Create or verify a provisioned administrative user."""
    if len(password) < 8:
        print("Error: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    if role not in ("admin", "supervisor", "viewer"):
        print(f"Error: Invalid role '{role}'. Must be admin, supervisor, or viewer.", file=sys.stderr)
        sys.exit(1)

    with SessionLocal() as session:
        existing = get_user_by_email(session, email)
        if existing:
            print(f"User '{email}' already exists (role={existing.role}, active={existing.is_active}).", file=sys.stderr)
            sys.exit(1)

        password_hash = hash_password(password)
        new_user = create_user(
            session=session,
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            role=role,
            is_active=True,
        )
        session.commit()
        print(f"Successfully provisioned {role} account: {new_user.email} (ID: {new_user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a HeatShield Bharat user account.")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--name", default=None, help="User display name")
    parser.add_argument("--role", default="admin", choices=["admin", "supervisor", "viewer"], help="User role")
    parser.add_argument("--password", default=None, help="User password (prompted if omitted)")

    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Enter password (min 8 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    provision_user(
        email=args.email,
        password=password,
        display_name=args.name,
        role=args.role,
    )


if __name__ == "__main__":
    main()
