"""
Tests for Clinical and Operational Departmental Routers.
Verifies the live hospital simulation endpoints across all key departments.
"""

def test_departments_directory(client):
    """Verifies that all 16 departments are registered in the metadata directory."""
    response = client.get("/api/departments")
    assert response.status_code == 200
    data = response.json()
    assert data["departments_count"] == 16
    assert "hospital" in data


def test_emergency_triage_endpoints(client):
    """Emergency department active triage queue and statistics."""
    triage_res = client.get("/api/emergency/triage")
    assert triage_res.status_code == 200
    data = triage_res.json()
    assert "data" in data or isinstance(data, list)

    stats_res = client.get("/api/emergency/stats")
    assert stats_res.status_code == 200
    assert "active_cases" in stats_res.json()


def test_opd_queues(client):
    """Outpatient department active tokens."""
    response = client.get("/api/opd/tokens")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_ipd_beds_census(client):
    """Inpatient bed tracking across wards."""
    response = client.get("/api/ipd/beds")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_icu_beds_and_telemetry(client):
    """ICU critical care telemetry and bed occupancy."""
    response = client.get("/api/icu/beds")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_ot_surgical_slate(client):
    """Operation Theatre master schedule."""
    response = client.get("/api/ot/schedule")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_laboratory_orders(client):
    """Laboratory Information System order tracking."""
    response = client.get("/api/laboratory/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_pharmacy_inventory(client):
    """Pharmacy stock and cold chain inventory."""
    response = client.get("/api/pharmacy/inventory")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_dialysis_stations(client):
    """Hemodialysis unit station telemetry."""
    response = client.get("/api/dialysis/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))


def test_billing_invoices(client):
    """Billing and PM-JAY claim adjudication."""
    response = client.get("/api/billing/invoices")
    assert response.status_code == 200
    assert isinstance(response.json(), (dict, list))
