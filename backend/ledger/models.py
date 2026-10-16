"""Ledger Data Structures and In-Memory Fallback Repository."""
from typing import Dict, List, Optional
from backend.shared.constants import LedgerStatus
from backend.shared.schemas import LedgerRecordSchema


class LedgerRepository:
    """In-memory audit ledger with database sync capability."""

    def __init__(self):
        self._records: Dict[str, LedgerRecordSchema] = {}

    def record_transaction(self, record: LedgerRecordSchema) -> LedgerRecordSchema:
        self._records[record.request_id] = record
        return record

    def get_record(self, request_id: str) -> Optional[LedgerRecordSchema]:
        return self._records.get(request_id)

    def list_records(
        self,
        status: Optional[str] = None,
        service_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LedgerRecordSchema]:
        results = list(self._records.values())
        if status:
            results = [r for r in results if r.status.value == status or r.status == status]
        if service_id:
            results = [r for r in results if r.service_id == service_id]

        # Sort by timestamp descending
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[offset : offset + limit]

    def count(self, status: Optional[str] = None, service_id: Optional[str] = None) -> int:
        return len(self.list_records(status=status, service_id=service_id, limit=100000))


# Global runtime instance
ledger_repo = LedgerRepository()
