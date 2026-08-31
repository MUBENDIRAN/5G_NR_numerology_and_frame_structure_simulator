"""CLI for the 5G NR Numerology and Frame-Structure Simulator.

Run from the project root:

    python main.py
    python main.py --export-all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.numerology import (
    SUPPORTED_NUMEROLOGIES,
    get_scheduling_granularity_ms,
    validate_numerology,
)
from src.simulator import create_comparison_table, export_comparison_csv
from src.timeline import build_frame, format_frame_summary
from src.visualization import plot_all_resource_grids, plot_resource_grid, plot_timing_comparison

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"

GRANULARITY_NOTE = (
    "Scheduling granularity is the slot duration in this simplified model. "
    "It is the theoretical minimum scheduling interval, not real "
    "end-to-end 5G network latency."
)

SYMBOL_NOTE = (
    "Symbol duration = slot duration / 14. Real NR cyclic-prefix timing "
    "makes a few symbols slightly longer than others; this simulator uses "
    "equal symbol widths as a simplification."
)


def _configure_stdout() -> None:
    """Use UTF-8 on Windows so μ prints correctly in modern terminals."""
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def _pause() -> None:
    try:
        input("\nPress Enter to return to the menu...")
    except EOFError:
        print()


def _read_numerology() -> int | None:
    raw = input(f"Enter numerology μ {list(SUPPORTED_NUMEROLOGIES)}: ").strip()
    try:
        mu = int(raw)
    except ValueError:
        print(f"'{raw}' is not an integer. μ must be 0, 1, 2 or 3.")
        return None
    try:
        return validate_numerology(mu)
    except ValueError as exc:
        print(exc)
        return None


def display_comparison() -> None:
    table = create_comparison_table()
    print()
    print("5G NR numerology comparison (normal cyclic prefix)")
    print("-" * 78)
    print(table.to_string(index=False))
    print()
    print(GRANULARITY_NOTE)
    print(SYMBOL_NOTE)


def display_frame_summary() -> None:
    mu = _read_numerology()
    if mu is None:
        return
    frame = build_frame(mu)
    print()
    print(format_frame_summary(frame))
    print()
    print(
        f"Theoretical scheduling granularity for μ={mu}: "
        f"{get_scheduling_granularity_ms(mu):g} ms"
    )


def generate_timing_plot() -> None:
    path = plot_timing_comparison(OUTPUT_DIR / "timing_comparison.png")
    print(f"Saved timing comparison plot: {path}")


def generate_resource_grid_plot() -> None:
    print("Enter a numerology, or type 'all' to generate μ = 0, 1, 2 and 3.")
    raw = input(f"μ {list(SUPPORTED_NUMEROLOGIES)} or all: ").strip().lower()
    if raw == "all":
        paths = plot_all_resource_grids(OUTPUT_DIR)
        print("Saved resource-grid plots:")
        for path in paths:
            print(f"  {path}")
        return
    try:
        mu = validate_numerology(int(raw))
    except ValueError as exc:
        print(exc)
        return
    path = plot_resource_grid(mu, OUTPUT_DIR / f"resource_grid_mu{mu}.png")
    print(f"Saved resource-grid plot: {path}")
    print(
        "The 12-subcarrier axis is an illustrative resource block. "
        "It is not a configured NR bandwidth."
    )


def export_csv() -> None:
    path = export_comparison_csv(OUTPUT_DIR / "numerology_comparison.csv")
    print(f"Saved comparison table: {path}")


def generate_all_deliverables() -> None:
    """Write the CSV and all PNG deliverables into outputs/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = export_comparison_csv(OUTPUT_DIR / "numerology_comparison.csv")
    timing_path = plot_timing_comparison(OUTPUT_DIR / "timing_comparison.png")
    grid_paths = plot_all_resource_grids(OUTPUT_DIR)
    print("Generated deliverable files:")
    print(f"  {csv_path}")
    print(f"  {timing_path}")
    for path in grid_paths:
        print(f"  {path}")


def print_menu() -> None:
    print()
    print("=" * 64)
    print("  5G NR Numerology and Frame-Structure Simulator")
    print("  SCS, slot and symbol timing  |  μ = 0, 1, 2, 3")
    print("=" * 64)
    print("  1. Display numerology comparison")
    print("  2. Display frame timeline summary for a selected μ")
    print("  3. Generate timing comparison plot")
    print("  4. Generate resource-grid / timeline plot")
    print("  5. Export comparison table as CSV")
    print("  6. Generate all deliverable files")
    print("  0. Exit")
    print("=" * 64)


def run_menu() -> None:
    actions = {
        "1": display_comparison,
        "2": display_frame_summary,
        "3": generate_timing_plot,
        "4": generate_resource_grid_plot,
        "5": export_csv,
        "6": generate_all_deliverables,
    }
    while True:
        print_menu()
        try:
            choice = input("Select an option: ").strip()
        except EOFError:
            print()
            break
        if choice in ("0", "q", "Q", "exit"):
            print("Exiting.")
            break
        action = actions.get(choice)
        if action is None:
            print("Please choose 0, 1, 2, 3, 4, 5 or 6.")
            continue
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - keep the CLI alive during a viva
            print(f"Error: {exc}")
        _pause()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "5G NR numerology and frame-structure simulator "
            "(SCS, slot and symbol timing)."
        )
    )
    parser.add_argument(
        "--export-all",
        action="store_true",
        help="Write CSV and PNG deliverables to outputs/ and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = parse_args(argv)
    if args.export_all:
        generate_all_deliverables()
        return 0
    run_menu()
    return 0


if __name__ == "__main__":
    sys.exit(main())
