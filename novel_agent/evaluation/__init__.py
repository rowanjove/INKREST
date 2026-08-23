"""Local, copyright-safe evaluation fixtures and metrics for long-form work."""

from .fixtures import build_consistency_fixtures, load_fixture_file
from .taxonomy import CONSISTENCY_TAXONOMY, ConsistencyCase, normalise_case

__all__ = [
    "CONSISTENCY_TAXONOMY",
    "ConsistencyCase",
    "build_consistency_fixtures",
    "load_fixture_file",
    "normalise_case",
]
