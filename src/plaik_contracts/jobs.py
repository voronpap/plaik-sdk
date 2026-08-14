"""Public job-execution contracts shared by Core and extensions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class JobExecutionContext:
    """One leased execution attempt delivered to a job handler.

    ``idempotency_key`` identifies the logical effect across retries, while the
    monotonically increasing ``fencing_token`` identifies this specific claim.
    A handler that performs an irreversible downstream effect must pass both to
    a provider capable of atomic idempotency and stale-token rejection.
    """

    job_id: str
    idempotency_key: str
    attempt: int
    fencing_token: int
    lease_owner: str
    lease_expires_at: datetime
    payload: Mapping[str, Any]
