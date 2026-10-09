"""
Real-time In-Memory Event Bus & WebSocket/SSE Broadcaster
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Set
from collections import deque
from app.config import EVENT_BUFFER_SIZE
from app.database import execute_insert

class HospitalEventBus:
    def __init__(self):
        self.recent_events: deque = deque(maxlen=EVENT_BUFFER_SIZE)
        self.subscribers: Set[asyncio.Queue] = set()
        self.icu_subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self.subscribers.discard(q)

    def subscribe_icu(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self.icu_subscribers.add(q)
        return q

    def unsubscribe_icu(self, q: asyncio.Queue):
        self.icu_subscribers.discard(q)

    async def broadcast_icu_telemetry(self, telemetry_data: Dict[str, Any]):
        for q in list(self.icu_subscribers):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                await q.put(telemetry_data)
            except Exception:
                self.icu_subscribers.discard(q)

    async def publish_event(
        self,
        department: str,
        event_type: str,
        severity: str,
        summary: str,
        uhid: str = None,
        patient_name: str = None,
        details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Publishes an event to memory buffer, subscribers, and database feed."""
        now_str = datetime.now().isoformat()
        event_id = f"EVT-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        details = details or {}

        event_payload = {
            "event_id": event_id,
            "timestamp": now_str,
            "department": department,
            "event_type": event_type,
            "severity": severity,
            "uhid": uhid,
            "patient_name": patient_name,
            "summary": summary,
            "details": details
        }

        # Save in memory buffer
        self.recent_events.appendleft(event_payload)

        # Asynchronously write to SQLite events feed
        try:
            execute_insert(
                """INSERT INTO hospital_events_feed 
                   (event_id, timestamp, department, event_type, severity, uhid, patient_name, summary, details_json) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    now_str,
                    department,
                    event_type,
                    severity,
                    uhid,
                    patient_name,
                    summary,
                    json.dumps(details)
                )
            )
        except Exception as e:
            # Silently log if DB locked, don't stall event stream
            pass

        # Broadcast to all live listeners
        for q in list(self.subscribers):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                await q.put(event_payload)
            except Exception:
                self.subscribers.discard(q)

        return event_payload

    def get_recent_events(self, limit: int = 50, department: str = None, severity: str = None) -> List[Dict[str, Any]]:
        events = list(self.recent_events)
        if department:
            events = [e for e in events if e["department"].lower() == department.lower()]
        if severity:
            events = [e for e in events if e["severity"].upper() == severity.upper()]
        return events[:limit]

# Singleton instance
event_bus = HospitalEventBus()
