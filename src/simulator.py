"""Orchestration layer: comparison table, granularity metric, CSV export.

This module does not plot figures and does not print. The CLI in main.py
decides what to display. Pandas is used here because a labelled table
and a CSV export are the main deliverable of this layer.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.numerology import (
    SUPPORTED_NUMEROLOGIES,
    get_scs_khz,
    get_scheduling_granularity_ms,
    get_slot_duration_ms,
    get_slots_per_frame,
    get_slots_per_subframe,
    get_symbol_duration_us,
    get_symbols_per_slot,
    validate_numerology,
)
from src.timeline import Frame, build_frame

COMPARISON_COLUMNS: tuple[str, ...] = (
    "mu",
    "scs_khz",
    "slot_duration_ms",
    "symbols_per_slot",
    "symbol_duration_us",
    "slots_per_subframe",
    "slots_per_frame",
    "scheduling_granularity_ms",
)

DISPLAY_COLUMNS: dict[str, str] = {
    "mu": "mu",
    "scs_khz": "SCS_kHz",
    "slot_duration_ms": "slot_duration_ms",
    "symbols_per_slot": "symbols_per_slot",
    "symbol_duration_us": "symbol_duration_us",
    "slots_per_subframe": "slots_per_subframe",
    "slots_per_frame": "slots_per_frame",
    "scheduling_granularity_ms": "scheduling_granularity_ms",
}


def calculate_numerology_result(mu: int) -> dict[str, float | int]:
    """Compute all timing metrics for a single numerology.

    Args:
        mu: Numerology index (0, 1, 2 or 3).

    Returns:
        A dictionary with the comparison-table fields for this μ.
    """
    mu = validate_numerology(mu)
    slot_duration_ms = get_slot_duration_ms(mu)
    return {
        "mu": mu,
        "scs_khz": get_scs_khz(mu),
        "slot_duration_ms": slot_duration_ms,
        "symbols_per_slot": get_symbols_per_slot(),
        "symbol_duration_us": get_symbol_duration_us(mu),
        "slots_per_subframe": get_slots_per_subframe(mu),
        "slots_per_frame": get_slots_per_frame(mu),
        "scheduling_granularity_ms": get_scheduling_granularity_ms(mu),
    }


def calculate_all_numerologies() -> list[dict[str, float | int]]:
    """Compute timing metrics for every supported numerology."""
    return [calculate_numerology_result(mu) for mu in SUPPORTED_NUMEROLOGIES]


def create_comparison_table() -> pd.DataFrame:
    """Return a pandas DataFrame comparing μ = 0, 1, 2, 3.

    scheduling_granularity_ms is identical to slot_duration_ms in this
    simplified model. It is the theoretical minimum scheduling interval,
    not measured 5G network latency.
    """
    rows = calculate_all_numerologies()
    table = pd.DataFrame(rows, columns=list(COMPARISON_COLUMNS))
    return table.rename(columns=DISPLAY_COLUMNS)


def build_frames_for_all_numerologies() -> dict[int, Frame]:
    """Build one 10 ms radio frame per supported numerology."""
    return {mu: build_frame(mu) for mu in SUPPORTED_NUMEROLOGIES}


def export_comparison_csv(output_path: str | Path) -> Path:
    """Write the numerology comparison table to a CSV file.

    Args:
        output_path: Destination path, typically outputs/numerology_comparison.csv.

    Returns:
        The resolved path that was written.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = create_comparison_table()
    table.to_csv(path, index=False, float_format="%.10g")
    return path.resolve()
