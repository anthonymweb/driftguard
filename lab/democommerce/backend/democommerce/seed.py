"""Seed the fictional catalogue used in repeatable local evaluations."""
from sqlalchemy import select

from . import models
from .main import CATALOGUE


def seed_catalogue(db):
    for row in CATALOGUE:
        slug, name, category, description, price, compare, stock, featured = row
        if not db.scalar(select(models.Product).where(models.Product.slug == slug)):
            db.add(models.Product(slug=slug, name=name, category=category, description=description,
                                  price_cents=price, compare_at_cents=compare, stock=stock, featured=featured))
