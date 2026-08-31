"""Frame → subframe → slot → symbol timeline for one 10 ms NR radio frame.

Timing is derived from the numerology calculations in numerology.py.
Nothing in this module hardcodes 0.5 ms / 0.25 ms / 0.125 ms values.

SIMPLIFICATION: each slot is split into 14 equal symbol intervals.
In real NR the cyclic prefix makes a few symbols slightly longer than
others. See numerology.py for the full note.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.numerology import (
    FRAME_DURATION_MS,
    SUBFRAME_DURATION_MS,
    SUBFRAMES_PER_FRAME,
    get_scs_khz,
    get_slot_duration_ms,
    get_slots_per_subframe,
    get_symbols_per_slot,
    validate_numerology,
)


@dataclass(frozen=True)
class Symbol:
    """One equalized OFDM symbol inside a slot.

    Attributes:
        index: Symbol index within the slot (0 .. 13 for normal CP).
        slot_index: Slot index within the parent subframe.
        subframe_index: Subframe index within the radio frame (0 .. 9).
        start_ms: Symbol start time relative to the start of the frame.
        end_ms: Symbol end time relative to the start of the frame.
        duration_ms: Equalized symbol duration (slot_duration / 14).
    """

    index: int
    slot_index: int
    subframe_index: int
    start_ms: float
    end_ms: float
    duration_ms: float


@dataclass(frozen=True)
class Slot:
    """One NR slot containing 14 equalized OFDM symbols (normal CP).

    Attributes:
        index: Slot index within the parent subframe (0 .. 2^μ - 1).
        subframe_index: Subframe index within the radio frame (0 .. 9).
        frame_slot_index: Slot index within the whole 10 ms frame.
        start_ms: Slot start time relative to the start of the frame.
        end_ms: Slot end time relative to the start of the frame.
        duration_ms: Slot duration from the numerology formulas.
        symbols: Ordered symbols that fill this slot.
    """

    index: int
    subframe_index: int
    frame_slot_index: int
    start_ms: float
    end_ms: float
    duration_ms: float
    symbols: tuple[Symbol, ...]


@dataclass(frozen=True)
class Subframe:
    """One 1 ms NR subframe containing 2^μ slots.

    Attributes:
        index: Subframe index within the radio frame (0 .. 9).
        start_ms: Subframe start time relative to the start of the frame.
        end_ms: Subframe end time relative to the start of the frame.
        duration_ms: Always 1.0 ms in NR.
        slots: Ordered slots that fill this subframe.
    """

    index: int
    start_ms: float
    end_ms: float
    duration_ms: float
    slots: tuple[Slot, ...]


@dataclass(frozen=True)
class Frame:
    """One 10 ms NR radio frame for a chosen numerology.

    Attributes:
        mu: Numerology index used to build this frame.
        scs_khz: Subcarrier spacing in kHz.
        start_ms: Always 0.0 in this simulator.
        end_ms: Always 10.0 ms (one radio frame).
        duration_ms: Always 10.0 ms.
        subframes: The 10 subframes that fill the radio frame.
    """

    mu: int
    scs_khz: float
    start_ms: float
    end_ms: float
    duration_ms: float
    subframes: tuple[Subframe, ...]

    @property
    def slot_count(self) -> int:
        """Total number of slots in the radio frame."""
        return sum(len(subframe.slots) for subframe in self.subframes)

    @property
    def symbol_count(self) -> int:
        """Total number of equalized symbols in the radio frame."""
        return sum(
            len(slot.symbols)
            for subframe in self.subframes
            for slot in subframe.slots
        )


def _build_symbols(
    *,
    slot_index: int,
    subframe_index: int,
    slot_start_ms: float,
    slot_end_ms: float,
    symbols_per_slot: int,
) -> tuple[Symbol, ...]:
    """Build equalized symbols that tile a slot without gaps or overlap."""
    slot_duration_ms = slot_end_ms - slot_start_ms
    symbol_duration_ms = slot_duration_ms / symbols_per_slot
    symbols: list[Symbol] = []
    for symbol_index in range(symbols_per_slot):
        start_ms = slot_start_ms + symbol_index * symbol_duration_ms
        # Snap the last symbol to the slot end so float drift cannot
        # leave a hole at the slot boundary.
        if symbol_index == symbols_per_slot - 1:
            end_ms = slot_end_ms
        else:
            end_ms = start_ms + symbol_duration_ms
        symbols.append(
            Symbol(
                index=symbol_index,
                slot_index=slot_index,
                subframe_index=subframe_index,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=end_ms - start_ms,
            )
        )
    return tuple(symbols)


def build_frame(mu: int) -> Frame:
    """Build one 10 ms radio frame for numerology μ.

    The hierarchy is Frame → 10 Subframes → 2^μ Slots each → 14 Symbols.

    Args:
        mu: Numerology index (0, 1, 2 or 3).

    Returns:
        An immutable Frame whose last symbol ends at 10 ms.
    """
    mu = validate_numerology(mu)
    scs_khz = get_scs_khz(mu)
    slots_per_subframe = get_slots_per_subframe(mu)
    slot_duration_ms = get_slot_duration_ms(mu)
    symbols_per_slot = get_symbols_per_slot()

    subframes: list[Subframe] = []
    for subframe_index in range(SUBFRAMES_PER_FRAME):
        subframe_start_ms = subframe_index * SUBFRAME_DURATION_MS
        subframe_end_ms = subframe_start_ms + SUBFRAME_DURATION_MS

        slots: list[Slot] = []
        for slot_index in range(slots_per_subframe):
            slot_start_ms = subframe_start_ms + slot_index * slot_duration_ms
            if slot_index == slots_per_subframe - 1:
                slot_end_ms = subframe_end_ms
            else:
                slot_end_ms = slot_start_ms + slot_duration_ms

            frame_slot_index = subframe_index * slots_per_subframe + slot_index
            symbols = _build_symbols(
                slot_index=slot_index,
                subframe_index=subframe_index,
                slot_start_ms=slot_start_ms,
                slot_end_ms=slot_end_ms,
                symbols_per_slot=symbols_per_slot,
            )
            slots.append(
                Slot(
                    index=slot_index,
                    subframe_index=subframe_index,
                    frame_slot_index=frame_slot_index,
                    start_ms=slot_start_ms,
                    end_ms=slot_end_ms,
                    duration_ms=slot_end_ms - slot_start_ms,
                    symbols=symbols,
                )
            )

        subframes.append(
            Subframe(
                index=subframe_index,
                start_ms=subframe_start_ms,
                end_ms=subframe_end_ms,
                duration_ms=SUBFRAME_DURATION_MS,
                slots=tuple(slots),
            )
        )

    return Frame(
        mu=mu,
        scs_khz=scs_khz,
        start_ms=0.0,
        end_ms=FRAME_DURATION_MS,
        duration_ms=FRAME_DURATION_MS,
        subframes=tuple(subframes),
    )


def iter_slots(frame: Frame):
    """Yield every slot in the frame in time order."""
    for subframe in frame.subframes:
        yield from subframe.slots


def iter_symbols(frame: Frame):
    """Yield every symbol in the frame in time order."""
    for slot in iter_slots(frame):
        yield from slot.symbols


def format_frame_summary(frame: Frame) -> str:
    """Return a viva-friendly text summary of one radio frame."""
    first_subframe = frame.subframes[0]
    last_subframe = frame.subframes[-1]
    last_slot = last_subframe.slots[-1]
    last_symbol = last_slot.symbols[-1]
    first_symbol = first_subframe.slots[0].symbols[0]

    lines: list[str] = [
        f"Radio frame summary for numerology μ = {frame.mu}",
        f"  SCS                      : {frame.scs_khz:g} kHz",
        f"  Frame duration           : {frame.duration_ms:g} ms",
        f"  Subframes in frame       : {len(frame.subframes)}",
        f"  Slots in frame           : {frame.slot_count}",
        f"  Symbols in frame         : {frame.symbol_count}",
        f"  Slot duration            : {first_subframe.slots[0].duration_ms:g} ms",
        f"  Equalized symbol duration: {first_symbol.duration_ms * 1000.0:.6f} us",
        "",
        f"First subframe (index {first_subframe.index}): "
        f"{first_subframe.start_ms:g} ms to {first_subframe.end_ms:g} ms",
    ]
    for slot in first_subframe.slots:
        first = slot.symbols[0]
        last = slot.symbols[-1]
        lines.append(
            f"  Slot {slot.index}: {slot.start_ms:.6f} .. {slot.end_ms:.6f} ms"
            f"  |  {len(slot.symbols)} symbols"
            f"  |  symbol 0 starts {first.start_ms:.6f} ms"
            f", symbol {last.index} ends {last.end_ms:.6f} ms"
        )

    lines.extend(
        [
            "",
            f"Last subframe (index {last_subframe.index}): "
            f"{last_subframe.start_ms:g} ms to {last_subframe.end_ms:g} ms",
            f"  Last slot {last_slot.index} (frame slot {last_slot.frame_slot_index}): "
            f"{last_slot.start_ms:.6f} .. {last_slot.end_ms:.6f} ms",
            f"  Last symbol ends at {last_symbol.end_ms:.6f} ms "
            f"(must equal {FRAME_DURATION_MS:g} ms)",
            "",
            "Note: symbol durations are equalized (slot duration / 14). "
            "This is a simulation simplification, not bit-accurate CP timing.",
            "Note: slot duration is theoretical scheduling granularity, "
            "not end-to-end network latency.",
        ]
    )
    return "\n".join(lines)
