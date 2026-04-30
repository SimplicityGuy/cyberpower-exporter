"""Pytest fixtures for cyberpower-exporter tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import REGISTRY
import pytest


if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _isolate_prometheus_registry() -> Iterator[None]:
    """Unregister any collectors created during the test.

    The exporter uses the global default ``REGISTRY``. Without this fixture
    each test that calls ``register_prometheus_collectors`` would explode on
    the second run with "Duplicated timeseries in CollectorRegistry".
    """
    before = set(REGISTRY._names_to_collectors.values())  # type: ignore[attr-defined]
    yield
    after = set(REGISTRY._names_to_collectors.values())  # type: ignore[attr-defined]
    for collector in after - before:
        REGISTRY.unregister(collector)
