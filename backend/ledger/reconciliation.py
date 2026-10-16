"""[DEFINED INTERFACE & RECONCILIATION] Settlement Reconciliation Worker."""
import logging
from typing import List
from backend.shared.constants import LedgerStatus
from backend.shared.schemas import LedgerRecordSchema
from backend.ledger.models import LedgerRepository, ledger_repo

logger = logging.getLogger(__name__)


class SettlementReconciler:
    """Audits and reconciles in-flight or disputed transactions."""

    def __init__(self, repository: LedgerRepository = ledger_repo):
        self.repo = repository

    async def reconcile_pending(self) -> List[LedgerRecordSchema]:
        """Audit records without transaction hash or in ambiguous status.
        Member 4 will connect this to periodic background task or cron.
        """
        all_records = self.repo.list_records(limit=1000)
        unsettled = [
            r for r in all_records
            if r.status == LedgerStatus.PAID and not r.tx_hash
        ]
        logger.info(f"Reconciliation run: {len(unsettled)} records awaiting on-chain confirmation.")
        return unsettled
