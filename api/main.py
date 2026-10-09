"""
api/main.py
Backwards-compatibility entrypoint for legacy launchers.
Re-exports the unified FastAPI application from app.main.
All 16 departments, 12 RBAC baseline endpoints, ontology, and simulation are included.
"""

from app.main import app

__all__ = ["app"]
