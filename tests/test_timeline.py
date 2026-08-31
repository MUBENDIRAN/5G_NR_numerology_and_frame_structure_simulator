"""Tests for the Frame → Subframe → Slot → Symbol timeline."""

from __future__ import annotations

import math
import unittest

from src.numerology import (
    FRAME_DURATION_MS,
    SUBFRAME_DURATION_MS,
    get_scs_khz,
    get_slot_duration_ms,
    get_slots_per_frame,
    get_slots_per_subframe,
    get_symbol_duration_us,
    get_symbols_per_slot,
)
from src.timeline import (
    Frame,
    Slot,
    Subframe,
    Symbol,
    build_frame,
    format_frame_summary,
    iter_slots,
    iter_symbols,
)


class TestBuildFrameRejectsInvalidMu(unittest.TestCase):
    def test_invalid_mu_raises_value_error(self) -> None:
        invalid_values = [-1, 4, 2.5, "two", None, True, False]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    build_frame(value)


class TestFrameHierarchy(unittest.TestCase):
    def test_frame_covers_exactly_10_ms_for_every_numerology(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                self.assertIsInstance(frame, Frame)
                self.assertEqual(frame.mu, mu)
                self.assertEqual(frame.scs_khz, get_scs_khz(mu))
                self.assertEqual(len(frame.subframes), 10)
                self.assertAlmostEqual(frame.start_ms, 0.0, places=12)
                self.assertAlmostEqual(frame.end_ms, FRAME_DURATION_MS, places=12)
                self.assertAlmostEqual(frame.duration_ms, FRAME_DURATION_MS, places=12)
                last_symbol = frame.subframes[-1].slots[-1].symbols[-1]
                self.assertAlmostEqual(last_symbol.end_ms, FRAME_DURATION_MS, places=9)

    def test_subframes_are_contiguous_one_ms_blocks(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                for index, subframe in enumerate(frame.subframes):
                    self.assertIsInstance(subframe, Subframe)
                    self.assertEqual(subframe.index, index)
                    self.assertAlmostEqual(
                        subframe.start_ms,
                        index * SUBFRAME_DURATION_MS,
                        places=12,
                    )
                    self.assertAlmostEqual(subframe.duration_ms, 1.0, places=12)
                    self.assertAlmostEqual(
                        subframe.end_ms - subframe.start_ms,
                        1.0,
                        places=12,
                    )
                for previous, current in zip(frame.subframes, frame.subframes[1:]):
                    self.assertTrue(
                        math.isclose(
                            previous.end_ms,
                            current.start_ms,
                            rel_tol=0.0,
                            abs_tol=1e-12,
                        )
                    )

    def test_slot_counts_match_numerology(self) -> None:
        expected_slots_per_subframe = {0: 1, 1: 2, 2: 4, 3: 8}
        expected_slots_per_frame = {0: 10, 1: 20, 2: 40, 3: 80}
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                self.assertEqual(len(frame.subframes[0].slots), expected_slots_per_subframe[mu])
                self.assertEqual(frame.slot_count, expected_slots_per_frame[mu])
                self.assertEqual(frame.slot_count, get_slots_per_frame(mu))
                self.assertEqual(
                    frame.slot_count,
                    10 * get_slots_per_subframe(mu),
                )

    def test_each_slot_contains_14_symbols(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                symbols_per_slot = get_symbols_per_slot()
                self.assertEqual(symbols_per_slot, 14)
                for slot in iter_slots(frame):
                    self.assertEqual(len(slot.symbols), symbols_per_slot)
                self.assertEqual(
                    frame.symbol_count,
                    frame.slot_count * symbols_per_slot,
                )


class TestSlotAndSymbolTiming(unittest.TestCase):
    def test_slots_tile_each_subframe_without_gaps(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                slot_duration_ms = get_slot_duration_ms(mu)
                for subframe in frame.subframes:
                    self.assertAlmostEqual(
                        subframe.slots[0].start_ms,
                        subframe.start_ms,
                        places=12,
                    )
                    self.assertAlmostEqual(
                        subframe.slots[-1].end_ms,
                        subframe.end_ms,
                        places=9,
                    )
                    for slot in subframe.slots:
                        self.assertIsInstance(slot, Slot)
                        self.assertAlmostEqual(slot.duration_ms, slot_duration_ms, places=9)
                        self.assertAlmostEqual(
                            slot.end_ms - slot.start_ms,
                            slot.duration_ms,
                            places=9,
                        )
                    for previous, current in zip(subframe.slots, subframe.slots[1:]):
                        self.assertTrue(
                            math.isclose(
                                previous.end_ms,
                                current.start_ms,
                                rel_tol=0.0,
                                abs_tol=1e-12,
                            )
                        )

    def test_symbols_tile_each_slot_without_gaps(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                expected_symbol_ms = get_symbol_duration_us(mu) / 1000.0
                for slot in iter_slots(frame):
                    first = slot.symbols[0]
                    last = slot.symbols[-1]
                    self.assertIsInstance(first, Symbol)
                    self.assertEqual(first.index, 0)
                    self.assertEqual(last.index, 13)
                    self.assertAlmostEqual(first.start_ms, slot.start_ms, places=12)
                    self.assertAlmostEqual(last.end_ms, slot.end_ms, places=9)
                    for symbol in slot.symbols:
                        self.assertAlmostEqual(
                            symbol.duration_ms,
                            expected_symbol_ms,
                            places=9,
                        )
                    for previous, current in zip(slot.symbols, slot.symbols[1:]):
                        self.assertTrue(
                            math.isclose(
                                previous.end_ms,
                                current.start_ms,
                                rel_tol=0.0,
                                abs_tol=1e-12,
                            )
                        )

    def test_frame_slot_index_is_unique_and_ordered(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                indexes = [slot.frame_slot_index for slot in iter_slots(frame)]
                self.assertEqual(indexes, list(range(frame.slot_count)))

    def test_symbol_parent_indexes_match_slot_and_subframe(self) -> None:
        frame = build_frame(2)
        for subframe in frame.subframes:
            for slot in subframe.slots:
                self.assertEqual(slot.subframe_index, subframe.index)
                for symbol in slot.symbols:
                    self.assertEqual(symbol.slot_index, slot.index)
                    self.assertEqual(symbol.subframe_index, subframe.index)


class TestTimelineHelpers(unittest.TestCase):
    def test_iter_slots_and_iter_symbols_are_time_ordered(self) -> None:
        frame = build_frame(3)
        slots = list(iter_slots(frame))
        symbols = list(iter_symbols(frame))
        self.assertEqual(len(slots), frame.slot_count)
        self.assertEqual(len(symbols), frame.symbol_count)
        slot_starts = [slot.start_ms for slot in slots]
        symbol_starts = [symbol.start_ms for symbol in symbols]
        self.assertEqual(slot_starts, sorted(slot_starts))
        self.assertEqual(symbol_starts, sorted(symbol_starts))
        self.assertAlmostEqual(symbols[0].start_ms, 0.0, places=12)
        self.assertAlmostEqual(symbols[-1].end_ms, FRAME_DURATION_MS, places=9)

    def test_dataclasses_are_frozen(self) -> None:
        frame = build_frame(0)
        subframe = frame.subframes[0]
        slot = subframe.slots[0]
        symbol = slot.symbols[0]
        with self.assertRaises(Exception):
            frame.mu = 1  # type: ignore[misc]
        with self.assertRaises(Exception):
            subframe.index = 9  # type: ignore[misc]
        with self.assertRaises(Exception):
            slot.index = 3  # type: ignore[misc]
        with self.assertRaises(Exception):
            symbol.index = 7  # type: ignore[misc]

    def test_format_frame_summary_contains_key_fields(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                summary = format_frame_summary(frame)
                self.assertIn(f"μ = {mu}", summary)
                self.assertIn(f"{frame.scs_khz:g} kHz", summary)
                self.assertIn("10 ms", summary)
                self.assertIn(f"Slots in frame           : {frame.slot_count}", summary)
                self.assertIn(f"Symbols in frame         : {frame.symbol_count}", summary)
                self.assertIn("Last symbol ends at 10.000000 ms", summary)
                self.assertIn("theoretical scheduling granularity", summary)
                self.assertIn("equalized", summary.lower())


if __name__ == "__main__":
    unittest.main()
