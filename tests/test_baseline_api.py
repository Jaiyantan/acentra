"""
Tests for Baseline Hospital Operations RBAC Endpoints.
Verifies permission verification, status codes, and data access.
"""

def test_patient_lookup_rbac_enforcement(client):
    """Accessing patient records without X-Staff-ID must return 403 Forbidden."""
    response = client.get("/patient/UHID-000001")
    assert response.status_code == 403
    assert "Missing X-Staff-ID" in response.json()["detail"]


def test_patient_lookup_success(client, doctor_headers):
    """Doctor with patient:read permission should successfully fetch patient record."""
    response = client.get("/patient/UHID-000001", headers=doctor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["uhid"] == "UHID-000001"
    assert "name" in data


def test_patient_search(client, doctor_headers):
    """Searching patients by name substring."""
    response = client.get("/patient/search?name=Senthil", headers=doctor_headers)
    assert response.status_code == 200
    patients = response.json()
    assert isinstance(patients, list)
    if patients:
        assert "Senthil" in patients[0]["name"]


def test_beds_available(client, doctor_headers):
    """Querying available beds across wards."""
    response = client.get("/beds/available", headers=doctor_headers)
    assert response.status_code == 200
    beds = response.json()
    assert isinstance(beds, list)


def test_billing_rbac_permission_check(client, doctor_headers, billing_headers):
    """Doctor lacks billing:read, so querying bill should return 403."""
    forbidden_res = client.get("/bill/UHID-000001", headers=doctor_headers)
    assert forbidden_res.status_code == 403

    # Billing staff has billing:read, so should not get 403
    allowed_res = client.get("/bill/UHID-000001", headers=billing_headers)
    assert allowed_res.status_code in [200, 404]


def test_baseline_stats(client):
    """Public stats endpoint returns row counts across baseline tables."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "patients" in stats
    assert "beds" in stats
    assert "staff" in stats


def test_table_inspector(client):
    """Table inspector endpoint allows querying rows of valid tables."""
    response = client.get("/api/tables/departments?limit=5")
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
