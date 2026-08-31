"""Matplotlib figures for timing comparison and an illustrative resource grid.

The resource-grid plots use 12 subcarriers only, matching one resource
block as a teaching sketch. They do NOT represent a configured NR
channel bandwidth or a complete physical resource grid.

All time-axis values come from build_frame() / numerology calculations.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

# Agg writes PNG files without opening a GUI window. This is the reliable
# choice on a normal Windows Python install during a CLI demo.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np

from src.numerology import (
    SUBFRAME_DURATION_MS,
    SUPPORTED_NUMEROLOGIES,
    get_slot_duration_ms,
    get_slots_per_subframe,
    get_symbols_per_slot,
    validate_numerology,
)
from src.simulator import calculate_all_numerologies
from src.timeline import Frame, build_frame

# One resource block has 12 subcarriers. Used only as an illustration.
ILLUSTRATIVE_SUBCARRIERS: int = 12

SLOT_COLOURS: tuple[str, ...] = (
    "#4C72B0",
    "#DD8452",
    "#55A868",
    "#C44E52",
    "#8172B3",
    "#937860",
    "#DA8BC3",
    "#8C8C8C",
)


def _slot_colormap(n_slots: int) -> ListedColormap:
    """Return a discrete colormap with one colour per slot in a subframe."""
    return ListedColormap(SLOT_COLOURS[:n_slots])


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def plot_timing_comparison(output_path: str | Path) -> Path:
    """Save a two-panel figure: granularity bars and 1 ms slot packing.

    The lower panel is the visual that examiners usually want:

        μ=0 → 1 slot in 1 ms
        μ=1 → 2 slots in 1 ms
        μ=2 → 4 slots in 1 ms
        μ=3 → 8 slots in 1 ms

    Args:
        output_path: Destination PNG path.

    Returns:
        The resolved path that was written.
    """
    path = Path(output_path)
    _ensure_parent(path)

    results = calculate_all_numerologies()
    mus = [row["mu"] for row in results]
    granularities = [row["scheduling_granularity_ms"] for row in results]
    scs_values = [row["scs_khz"] for row in results]
    labels = [f"μ={mu}\n{scs:g} kHz" for mu, scs in zip(mus, scs_values)]

    fig, (ax_bar, ax_pack) = plt.subplots(
        2,
        1,
        figsize=(10.5, 8.5),
        gridspec_kw={"height_ratios": [1.15, 1.55]},
    )

    bar_colours = [SLOT_COLOURS[i] for i in range(len(mus))]
    bars = ax_bar.bar(labels, granularities, color=bar_colours, edgecolor="black", linewidth=0.6)
    ax_bar.set_ylabel("Theoretical scheduling granularity (ms)")
    ax_bar.set_title(
        "NR numerology timing comparison\n"
        "Scheduling granularity = slot duration in this simplified model"
    )
    ax_bar.set_ylim(0, 1.15)
    ax_bar.grid(axis="y", linestyle="--", alpha=0.4)
    for bar, value in zip(bars, granularities):
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.03,
            f"{value:g} ms",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax_bar.text(
        0.0,
        -0.22,
        "This is NOT end-to-end network latency. Propagation, core-network delay, "
        "queuing, HARQ and processing delay are not simulated.",
        transform=ax_bar.transAxes,
        fontsize=8,
        style="italic",
    )

    # Slot packing uses the actual first-subframe boundaries from build_frame().
    yticks = []
    yticklabels = []
    for row_index, mu in enumerate(SUPPORTED_NUMEROLOGIES):
        frame = build_frame(mu)
        subframe = frame.subframes[0]
        n_slots = len(subframe.slots)
        y = len(SUPPORTED_NUMEROLOGIES) - 1 - row_index
        yticks.append(y)
        yticklabels.append(f"μ={mu}  ({n_slots} slot{'s' if n_slots != 1 else ''})")
        for slot in subframe.slots:
            ax_pack.barh(
                y,
                slot.end_ms - slot.start_ms,
                left=slot.start_ms,
                height=0.62,
                color=SLOT_COLOURS[slot.index % len(SLOT_COLOURS)],
                edgecolor="black",
                linewidth=0.7,
            )
            ax_pack.text(
                (slot.start_ms + slot.end_ms) / 2.0,
                y,
                f"S{slot.index}",
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                fontweight="bold",
            )

    ax_pack.set_yticks(yticks)
    ax_pack.set_yticklabels(yticklabels)
    ax_pack.set_xlim(0.0, SUBFRAME_DURATION_MS)
    ax_pack.set_xlabel("Time within one 1 ms subframe (ms)")
    ax_pack.set_title("How many slots fit inside 1 ms as μ increases")
    ax_pack.set_ylim(-0.7, len(SUPPORTED_NUMEROLOGIES) - 0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.resolve()


def _draw_resource_grid(ax, frame: Frame) -> None:
    """Draw one illustrative RB (12 subcarriers) across the first 1 ms subframe."""
    subframe = frame.subframes[0]
    n_slots = len(subframe.slots)
    n_symbols = get_symbols_per_slot()
    n_sc = ILLUSTRATIVE_SUBCARRIERS

    time_edges = [symbol.start_ms for slot in subframe.slots for symbol in slot.symbols]
    time_edges.append(subframe.slots[-1].symbols[-1].end_ms)
    time_edges_arr = np.asarray(time_edges, dtype=float)
    sc_edges = np.arange(n_sc + 1, dtype=float) - 0.5

    # Each column is one equalized symbol; colour encodes slot index.
    grid = np.zeros((n_sc, n_slots * n_symbols), dtype=float)
    column = 0
    for slot in subframe.slots:
        for _symbol in slot.symbols:
            grid[:, column] = slot.index
            column += 1

    cmap = _slot_colormap(n_slots)
    bounds = np.arange(-0.5, n_slots, 1.0)
    norm = BoundaryNorm(bounds, cmap.N)
    mesh = ax.pcolormesh(
        time_edges_arr,
        sc_edges,
        grid,
        cmap=cmap,
        norm=norm,
        shading="flat",
        edgecolors="none",
    )

    for slot in subframe.slots:
        ax.axvline(slot.start_ms, color="black", linewidth=0.9)
        for symbol in slot.symbols[1:]:
            ax.axvline(symbol.start_ms, color="white", linewidth=0.35, alpha=0.55)
    ax.axvline(subframe.end_ms, color="black", linewidth=0.9)

    ax.set_xlim(subframe.start_ms, subframe.end_ms)
    ax.set_ylim(sc_edges[0], sc_edges[-1])
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Illustrative subcarrier index\n(12 subcarriers = 1 RB sketch)")
    ax.set_yticks(list(range(n_sc)))
    ax.set_title(
        f"Illustrative resource-grid timeline  |  μ={frame.mu}, "
        f"SCS={frame.scs_khz:g} kHz, {n_slots} slot(s) in 1 ms"
    )

    cbar = ax.figure.colorbar(mesh, ax=ax, ticks=list(range(n_slots)), pad=0.02)
    cbar.set_label("Slot index inside the subframe")


def _draw_frame_slot_timeline(ax, frame: Frame) -> None:
    """Draw all slots of the 10 ms radio frame as a single-row timeline."""
    for slot in (s for sf in frame.subframes for s in sf.slots):
        ax.barh(
            0,
            slot.end_ms - slot.start_ms,
            left=slot.start_ms,
            height=0.55,
            color=SLOT_COLOURS[slot.index % len(SLOT_COLOURS)],
            edgecolor="black",
            linewidth=0.25,
        )

    for subframe in frame.subframes:
        ax.axvline(subframe.start_ms, color="#333333", linewidth=0.8, linestyle=":")
    ax.axvline(frame.end_ms, color="#333333", linewidth=0.8, linestyle=":")

    ax.set_xlim(frame.start_ms, frame.end_ms)
    ax.set_ylim(-0.7, 0.7)
    ax.set_yticks([0])
    ax.set_yticklabels(["slots"])
    ax.set_xlabel("Time within one 10 ms radio frame (ms)")
    ax.set_title(
        f"Frame slot timeline  |  {frame.slot_count} slots, "
        f"each {get_slot_duration_ms(frame.mu):g} ms"
    )
    legend_handles = [
        Patch(
            facecolor=SLOT_COLOURS[i],
            edgecolor="black",
            label=f"Slot {i} in subframe",
        )
        for i in range(get_slots_per_subframe(frame.mu))
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.42),
        ncol=min(8, get_slots_per_subframe(frame.mu)),
        fontsize=8,
        frameon=False,
    )


def plot_resource_grid(mu: int, output_path: str | Path) -> Path:
    """Save the illustrative RB grid (1 ms) plus the 10 ms slot timeline.

    Args:
        mu: Numerology index (0, 1, 2 or 3).
        output_path: Destination PNG path.

    Returns:
        The resolved path that was written.
    """
    mu = validate_numerology(mu)
    path = Path(output_path)
    _ensure_parent(path)
    frame = build_frame(mu)

    fig, (ax_grid, ax_time) = plt.subplots(
        2,
        1,
        figsize=(12.5, 8.2),
        gridspec_kw={"height_ratios": [2.4, 1.0]},
    )
    _draw_resource_grid(ax_grid, frame)
    _draw_frame_slot_timeline(ax_time, frame)

    fig.suptitle(
        "Illustrative only: 12 subcarriers represent one resource block. "
        "This is not a configured NR bandwidth or a full physical resource grid.\n"
        "Symbol widths are equalized (slot duration / 14); real CP timing is slightly uneven.",
        fontsize=9,
        y=0.98,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.resolve()


def plot_all_resource_grids(output_dir: str | Path) -> list[Path]:
    """Save resource_grid_mu0.png ... resource_grid_mu3.png into output_dir."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for mu in SUPPORTED_NUMEROLOGIES:
        paths.append(plot_resource_grid(mu, directory / f"resource_grid_mu{mu}.png"))
    return paths
