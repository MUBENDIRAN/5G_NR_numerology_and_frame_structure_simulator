"""5G NR numerology and frame-structure simulator package."""

from src.numerology import (
    FRAME_DURATION_MS,
    SUBFRAME_DURATION_MS,
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

__all__ = [
    "FRAME_DURATION_MS",
    "SUBFRAME_DURATION_MS",
    "SUPPORTED_NUMEROLOGIES",
    "get_scs_khz",
    "get_scheduling_granularity_ms",
    "get_slot_duration_ms",
    "get_slots_per_frame",
    "get_slots_per_subframe",
    "get_symbol_duration_us",
    "get_symbols_per_slot",
    "validate_numerology",
]
