"""
run_server.py
Unified Launcher for Saveetha Medical College & Hospital (SMCH) Operations Engine.
Runs the complete FastAPI application exposing:
- 16 Departmental Operational Endpoints (Emergency, OPD, IPD, ICU, OT, LIS, RIS, etc.)
- 12 Baseline RBAC Endpoints for Static Specification Compatibility
- 24/7 Live Simulation Engine & Real-Time Telemetry Event Bus
- Operational Ontology, Cognee Knowledge Graph & Governed Operations Agent
- Hospital Command Center Web Dashboard at http://127.0.0.1:8000
"""

import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    print("=" * 75)
    print("  SAVEETHA MEDICAL COLLEGE & HOSPITAL (SMCH) OPERATIONS PLATFORM")
    print("  Acentra Operations Intelligence Engine & 24/7 Autonomous Digital Twin")
    print("=" * 75)
    print(f"  • Hospital Command Center:  http://127.0.0.1:{port}")
    print(f"  • Interactive Swagger Docs: http://127.0.0.1:{port}/docs")
    print(f"  • Operational Ontology UI:  http://127.0.0.1:{port}/ontology")
    print(f"  • 16 Clinical Departments:  23 API Routers Mounted")
    print(f"  • Agentic Security Defense: 6 Vectors Guarded • 8-Role RBAC Active")
    print("=" * 75)

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
