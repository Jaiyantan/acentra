"""
Pytest configuration and test fixtures for SMCH Operations Engine.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped test client for the unified FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def doctor_headers():
    """Headers for Doctor STF-001 (patient:read, admission:read, beds:read, approvals:read)."""
    return {"X-Staff-ID": "STF-001"}


@pytest.fixture
def nurse_headers():
    """Headers for Nurse STF-002 (patient:read, admission:read, beds:read)."""
    return {"X-Staff-ID": "STF-002"}


@pytest.fixture
def billing_headers():
    """Headers for Billing Staff STF-005 (patient:read, admission:read, billing:read)."""
    return {"X-Staff-ID": "STF-005"}


@pytest.fixture
def insurance_headers():
    """Headers for Insurance Staff STF-004 (patient:read, admission:read, beds:read, insurance:read)."""
    return {"X-Staff-ID": "STF-004"}


@pytest.fixture
def audit_headers():
    """Headers for Audit Staff STF-008 (patient:read, admission:read, audit:read)."""
    return {"X-Staff-ID": "STF-008"}


@pytest.fixture
def it_headers():
    """Headers for IT Support STF-010 (tickets:read, audit:read)."""
    return {"X-Staff-ID": "STF-010"}
