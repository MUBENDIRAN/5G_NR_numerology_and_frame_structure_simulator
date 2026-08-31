"""Pure 5G NR numerology calculations for μ = 0, 1, 2, 3.

Formulas used (normal cyclic prefix, simplified teaching model):

    SCS_kHz              = 15 * 2^μ
    slots_per_subframe   = 2^μ
    slot_duration_ms     = 1 / 2^μ          (subframe is always 1 ms)
    slots_per_frame      = 10 * 2^μ         (frame is always 10 ms)
    symbols_per_slot     = 14               (normal CP)
    symbol_duration_us   = (slot_duration_ms / 14) * 1000

SIMPLIFICATION — equal symbol duration
    Real NR OFDM symbols do not all have identical physical duration,
    because the cyclic prefix (CP) length differs for the first symbol
    in a slot/half-slot compared with the remaining symbols.
    This simulator divides the slot evenly across 14 symbols so that
    timing relationships stay easy to explain. Do not treat the
    resulting symbol_duration as a bit-accurate 3GPP CP timeline.

SCHEDULING GRANULARITY — not network latency
    Slot duration is reported as theoretical scheduling granularity
    (minimum scheduling interval) in this model. It is NOT real
    end-to-end 5G network latency. Propagation delay, core-network
    delay, queuing, HARQ, and processing delay are not simulated.
"""

from __future__ import annotations

SUPPORTED_NUMEROLOGIES: tuple[int, ...] = (0, 1, 2, 3)

# 3GPP TS 38.211: Δf = 15 kHz × 2^μ
BASE_SCS_KHZ: float = 15.0

# Normal cyclic prefix: 14 OFDM symbols per slot (TS 38.211).
SYMBOLS_PER_SLOT_NORMAL_CP: int = 14

# NR time-domain constants independent of numerology.
SUBFRAME_DURATION_MS: float = 1.0
FRAME_DURATION_MS: float = 10.0
SUBFRAMES_PER_FRAME: int = 10


def validate_numerology(mu: int) -> int:
    """Validate that μ is a supported NR numerology for this project.

    Supported values are the integers 0, 1, 2 and 3.

    Args:
        mu: Numerology index μ.

    Returns:
        The same integer μ if it is valid.

    Raises:
        ValueError: If μ is not an integer, or is outside {0, 1, 2, 3}.
            This includes values such as -1, 4, 2.5, and "two".
    """
    if isinstance(mu, bool) or not isinstance(mu, int):
        raise ValueError(
            "Numerology μ must be an integer in {0, 1, 2, 3}. "
            f"Received {mu!r} (type {type(mu).__name__})."
        )
    if mu not in SUPPORTED_NUMEROLOGIES:
        raise ValueError(
            f"Numerology μ={mu} is not supported in this simulator. "
            f"Supported values are {list(SUPPORTED_NUMEROLOGIES)}."
        )
    return mu


def get_scs_khz(mu: int) -> float:
    """Return subcarrier spacing in kHz: SCS = 15 × 2^μ.

    Args:
        mu: Numerology index μ.

    Returns:
        Subcarrier spacing in kilohertz (15, 30, 60 or 120).
    """
    mu = validate_numerology(mu)
    return BASE_SCS_KHZ * (2**mu)


def get_slots_per_subframe(mu: int) -> int:
    """Return the number of slots in one 1 ms subframe: 2^μ.

    Args:
        mu: Numerology index μ.

    Returns:
        Slots per subframe (1, 2, 4 or 8).
    """
    mu = validate_numerology(mu)
    return 2**mu


def get_slot_duration_ms(mu: int) -> float:
    """Return slot duration in milliseconds: 1 / 2^μ.

    One subframe is always 1 ms, so slot duration shrinks as μ grows.

    Args:
        mu: Numerology index μ.

    Returns:
        Slot duration in milliseconds (1.0, 0.5, 0.25 or 0.125).
    """
    mu = validate_numerology(mu)
    return SUBFRAME_DURATION_MS / get_slots_per_subframe(mu)


def get_slots_per_frame(mu: int) -> int:
    """Return the number of slots in one 10 ms radio frame: 10 × 2^μ.

    Args:
        mu: Numerology index μ.

    Returns:
        Slots per frame (10, 20, 40 or 80).
    """
    mu = validate_numerology(mu)
    return SUBFRAMES_PER_FRAME * get_slots_per_subframe(mu)


def get_symbols_per_slot() -> int:
    """Return OFDM symbols per slot for normal cyclic prefix (14).

    Extended CP (12 symbols) is out of scope for this project.
    """
    return SYMBOLS_PER_SLOT_NORMAL_CP


def get_symbol_duration_us(mu: int) -> float:
    """Return the equalized OFDM symbol duration in microseconds.

    SIMPLIFICATION: real NR symbol durations are not identical because
    cyclic-prefix lengths differ within a slot. This function uses

        symbol_duration_us = (slot_duration_ms / 14) * 1000

    so students can relate slot timing to a uniform symbol grid.

    Args:
        mu: Numerology index μ.

    Returns:
        Equalized symbol duration in microseconds.
    """
    mu = validate_numerology(mu)
    slot_duration_ms = get_slot_duration_ms(mu)
    symbol_duration_ms = slot_duration_ms / get_symbols_per_slot()
    return symbol_duration_ms * 1000.0


def get_scheduling_granularity_ms(mu: int) -> float:
    """Return theoretical scheduling granularity (minimum scheduling interval).

    In this simplified simulator the value equals slot duration.

    This is NOT real end-to-end network latency. The model does not
    include propagation delay, core-network delay, queuing, HARQ
    round-trip time, or UE/gNB processing delay.

    Args:
        mu: Numerology index μ.

    Returns:
        Scheduling granularity in milliseconds.
    """
    return get_slot_duration_ms(mu)
