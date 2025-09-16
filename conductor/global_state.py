"""Shared state utilities available to all nodes."""
from __future__ import annotations

import asyncio
from multiprocessing import Manager
from typing import Any, Dict, Iterable, MutableMapping, Optional

__all__ = ["GlobalState", "get_global_state", "set_initial_state", "child_initializer", "get_shared_proxy"]


_MANAGER = Manager()
_SHARED_PROXY = _MANAGER.dict()


class GlobalState:
    """Container for shared state accessible from inline and process nodes."""

    def __init__(self, storage: MutableMapping[str, Any]):
        self._storage = storage
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Async API
    # ------------------------------------------------------------------
    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._storage[key] = value

    async def get(self, key: str, default: Any = None) -> Any:
        return self._storage.get(key, default)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._storage.pop(key, None)

    async def update(self, mapping: MutableMapping[str, Any] | Iterable[tuple[str, Any]]) -> None:
        async with self._lock:
            if isinstance(mapping, MutableMapping):
                self._storage.update(mapping)
            else:
                for key, value in mapping:
                    self._storage[key] = value

    # ------------------------------------------------------------------
    # Sync helpers (usable from node code running in threads/processes)
    # ------------------------------------------------------------------
    def set_sync(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def get_sync(self, key: str, default: Any = None) -> Any:
        return self._storage.get(key, default)

    def delete_sync(self, key: str) -> None:
        self._storage.pop(key, None)

    def update_sync(self, mapping: MutableMapping[str, Any] | Iterable[tuple[str, Any]]) -> None:
        if isinstance(mapping, MutableMapping):
            self._storage.update(mapping)
        else:
            for key, value in mapping:
                self._storage[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._storage)

    def get_proxy(self):
        """Return the underlying proxy object for multiprocessing initialisation."""
        return self._storage


_GLOBAL_STATE = GlobalState(_SHARED_PROXY)


def get_global_state() -> GlobalState:
    """Return the global state instance."""
    return _GLOBAL_STATE


def set_initial_state(data: Optional[Dict[str, Any]] = None) -> None:
    """Populate the shared state with predefined values."""
    if not data:
        return
    _GLOBAL_STATE.update_sync(data)


def _set_proxy(proxy: MutableMapping[str, Any]) -> None:
    global _GLOBAL_STATE
    _GLOBAL_STATE = GlobalState(proxy)


def child_initializer(proxy: MutableMapping[str, Any]) -> None:  # pragma: no cover - executed in child processes
    """Initializer used by worker processes to reuse the parent's shared state."""
    _set_proxy(proxy)


def get_shared_proxy():
    return _GLOBAL_STATE.get_proxy()

