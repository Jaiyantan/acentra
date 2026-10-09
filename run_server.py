"""
Launcher script for Hospital Operations Simulation.
Runs the FastAPI application on http://127.0.0.1:8000 (or custom port).
Pure static data environment exposing the 14 SQLite tables through 12 endpoints.
"""

import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    print("=" * 70)
    print("HOSPITAL OPERATIONS SIMULATION (STATIC DATA ENVIRONMENT)")
    print("14 SQLite Tables • 12 RBAC API Endpoints • Seed Data & Knowledge Base")
    print(f"API Server: http://127.0.0.1:{port}")
    print(f"Interactive Swagger Docs: http://127.0.0.1:{port}/docs")
    print("=" * 70)
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
