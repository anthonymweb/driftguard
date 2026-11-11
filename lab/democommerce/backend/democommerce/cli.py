"""Research administrator bootstrap: python -m democommerce.cli create-admin EMAIL"""
import argparse
import getpass

from sqlalchemy import select

from . import models
from .database import Base, SessionLocal, engine
from .security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create a DemoCommerce researcher administrator")
    parser.add_argument("command", choices=["create-admin"])
    parser.add_argument("email")
    args = parser.parse_args()
    password = getpass.getpass("New administrator password (10+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 10 or password != confirm:
        parser.error("passwords must match and contain at least 10 characters")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        email = args.email.strip().lower()
        user = db.scalar(select(models.User).where(models.User.email == email))
        if user:
            parser.error("an account with that email already exists")
        db.add(models.User(email=email, full_name="Research Administrator", role="admin", password_hash=hash_password(password)))
        db.commit()
    print(f"Research administrator created: {email}")


if __name__ == "__main__":
    main()
