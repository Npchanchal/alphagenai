"""One process-wide lock for the in-memory stores the filing walks share.

The India and US walks run on separate threads. Network fetches and model reads
happen outside the lock; every change to the dataset, document index, coverage
stamps, overlays and ledger happens inside it, so a save never serialises a dict
another thread is resizing.
"""

from __future__ import annotations

import functools
import threading
from typing import Any, Callable, TypeVar

STORE_LOCK = threading.RLock()

F = TypeVar("F", bound=Callable[..., Any])


def locked(fn: F) -> F:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with STORE_LOCK:
            return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
