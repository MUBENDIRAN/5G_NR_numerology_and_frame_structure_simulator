"""Tests for NR numerology calculations and frame-timeline invariants."""

from __future__ import annotations

import math
import unittest

from src.numerology import (
    FRAME_DURATION_MS,
    SUBFRAME_DURATION_MS,
    get_scs_khz,
    get_scheduling_granularity_ms,
    get_slot_duration_ms,
    get_slots_per_frame,
    get_slots_per_subframe,
    get_symbol_duration_us,
    get_symbols_per_slot,
    validate_numerology,
)
from src.simulator import calculate_all_numerologies, create_comparison_table
from src.timeline import build_frame, iter_slots, iter_symbols


class TestNumerologyCalculations(unittest.TestCase):
    """Expected values follow SCS = 15 × 2^μ and slots_per_subframe = 2^μ."""

    def test_scs_khz_for_supported_numerologies(self) -> None:
        expected = {0: 15.0, 1: 30.0, 2: 60.0, 3: 120.0}
        for mu, scs in expected.items():
            with self.subTest(mu=mu):
                self.assertEqual(get_scs_khz(mu), scs)

    def test_slot_duration_ms_for_supported_numerologies(self) -> None:
        expected = {0: 1.0, 1: 0.5, 2: 0.25, 3: 0.125}
        for mu, duration in expected.items():
            with self.subTest(mu=mu):
                self.assertEqual(get_slot_duration_ms(mu), duration)

    def test_symbols_per_slot_is_always_14(self) -> None:
        self.assertEqual(get_symbols_per_slot(), 14)

    def test_slots_per_subframe(self) -> None:
        expected = {0: 1, 1: 2, 2: 4, 3: 8}
        for mu, count in expected.items():
            with self.subTest(mu=mu):
                self.assertEqual(get_slots_per_subframe(mu), count)

    def test_slots_per_frame(self) -> None:
        expected = {0: 10, 1: 20, 2: 40, 3: 80}
        for mu, count in expected.items():
            with self.subTest(mu=mu):
                self.assertEqual(get_slots_per_frame(mu), count)

    def test_slots_per_frame_is_ten_times_slots_per_subframe(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                self.assertEqual(
                    get_slots_per_frame(mu),
                    10 * get_slots_per_subframe(mu),
                )

    def test_slots_per_subframe_times_slot_duration_equals_one_ms(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                product = get_slots_per_subframe(mu) * get_slot_duration_ms(mu)
                self.assertAlmostEqual(product, SUBFRAME_DURATION_MS, places=12)

    def test_equalized_symbol_duration_times_14_equals_slot_duration(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                symbol_ms = get_symbol_duration_us(mu) / 1000.0
                reconstructed = symbol_ms * get_symbols_per_slot()
                self.assertAlmostEqual(reconstructed, get_slot_duration_ms(mu), places=12)

    def test_scheduling_granularity_equals_slot_duration(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                self.assertEqual(
                    get_scheduling_granularity_ms(mu),
                    get_slot_duration_ms(mu),
                )

    def test_validate_numerology_accepts_supported_values(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                self.assertEqual(validate_numerology(mu), mu)


class TestInvalidNumerology(unittest.TestCase):
    def test_invalid_mu_values_raise_value_error(self) -> None:
        invalid_values = [-1, 4, 2.5, "two", None, True, False, 99, 1.0]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_numerology(value)

    def test_invalid_mu_is_rejected_by_scs_function(self) -> None:
        with self.assertRaises(ValueError):
            get_scs_khz(-1)
        with self.assertRaises(ValueError):
            get_scs_khz(4)


class TestFrameTimeline(unittest.TestCase):
    def test_frame_covers_exactly_10_ms(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                self.assertEqual(len(frame.subframes), 10)
                self.assertAlmostEqual(frame.start_ms, 0.0, places=12)
                self.assertAlmostEqual(frame.end_ms, FRAME_DURATION_MS, places=12)
                self.assertAlmostEqual(frame.duration_ms, FRAME_DURATION_MS, places=12)
                last_symbol = frame.subframes[-1].slots[-1].symbols[-1]
                self.assertAlmostEqual(last_symbol.end_ms, FRAME_DURATION_MS, places=9)

    def test_each_subframe_is_one_ms(self) -> None:
        frame = build_frame(2)
        for subframe in frame.subframes:
            with self.subTest(subframe=subframe.index):
                self.assertAlmostEqual(subframe.duration_ms, 1.0, places=12)
                self.assertAlmostEqual(
                    subframe.end_ms - subframe.start_ms,
                    1.0,
                    places=12,
                )

    def test_slot_and_symbol_counts_match_numerology(self) -> None:
        for mu in (0, 1, 2, 3):
            with self.subTest(mu=mu):
                frame = build_frame(mu)
                self.assertEqual(frame.slot_count, get_slots_per_frame(mu))
                self.assertEqual(
                    frame.symbol_count,
                    get_slots_per_frame(mu) * get_symbols_per_slot(),
                )
                self.assertEqual(len(list(iter_slots(frame))), frame.slot_count)
                self.assertEqual(len(list(iter_symbols(frame))), frame.symbol_count)

    def test_symbols_tile_each_slot_without_gaps(self) -> None:
        frame = build_frame(3)
        for slot in iter_slots(frame):
            self.assertEqual(len(slot.symbols), 14)
            self.assertAlmostEqual(slot.symbols[0].start_ms, slot.start_ms, places=12)
            self.assertAlmostEqual(slot.symbols[-1].end_ms, slot.end_ms, places=9)
            for previous, current in zip(slot.symbols, slot.symbols[1:]):
                self.assertTrue(math.isclose(previous.end_ms, current.start_ms, rel_tol=0.0, abs_tol=1e-12))

    def test_scs_on_frame_matches_formula(self) -> None:
        frame = build_frame(1)
        self.assertEqual(frame.mu, 1)
        self.assertEqual(frame.scs_khz, 30.0)


class TestSimulatorTable(unittest.TestCase):
    def test_comparison_table_has_four_rows_and_required_columns(self) -> None:
        rows = calculate_all_numerologies()
        self.assertEqual(len(rows), 4)
        required = {
            "mu",
            "scs_khz",
            "slot_duration_ms",
            "symbols_per_slot",
            "symbol_duration_us",
            "slots_per_subframe",
            "slots_per_frame",
            "scheduling_granularity_ms",
        }
        self.assertTrue(required.issubset(rows[0].keys()))

        table = create_comparison_table()
        self.assertEqual(len(table), 4)
        self.assertIn("scheduling_granularity_ms", table.columns)


if __name__ == "__main__":
    unittest.main()
