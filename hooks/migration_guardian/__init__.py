"""
Migration Guardian - Database Migration Safety Hook for FastAPI + SQLAlchemy + Alembic
Protects against dangerous migrations and automates migration generation for modular architecture
"""

from .main import MigrationGuardian

__all__ = ['MigrationGuardian']