"""Wall spread over time: (price at max ask volume) - (price at max bid volume) on L1-L3."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_paths import ROUND_NUM, TICK_OFFSET, load_round1_frames  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / f"round{ROUND_NUM}_wall_spread.png"

DAY_BOUNDARIES = (TICK_OFFSET, 2 * TICK_OFFSET)
DAY_XTICKS = (TICK_OFFSET / 3, TICK_OFFSET + TICK_OFFSET / 3, 2 * TICK_OFFSET + TICK_OFFSET / 3)
DAY_LABELS = ("Day -2", "Day -1", "Day 0")

BID_P = ("bid_price_1", "bid_price_2", "bid_price_3")
BID_V = ("bid_volume_1", "bid_volume_2", "bid_volume_3")
ASK_P = ("ask_price_1", "ask_price_2", "ask_price_3")
ASK_V = ("ask_volume_1", "ask_volume_2", "ask_volume_3")


def _wall_price(prices: np.ndarray, vols: np.ndarray) -> np.ndarray:
    """Per row: price at the level with maximum volume (among finite levels)."""
    n, L = prices.shape
    out = np.full(n, np.nan, dtype=float)
    for i in range(n):
        p, v = prices[i], vols[i]
        mask = np.isfinite(p) & np.isfinite(v)
        if not mask.any():
            continue
        j = int(np.argmax(np.where(mask, v, -np.inf)))
        out[i] = p[j]
    return out


def wall_spread_series(df: pd.DataFrame) -> np.ndarray:
    wb = _wall_price(
        df[list(BID_P)].to_numpy(dtype=float),
        df[list(BID_V)].to_numpy(dtype=float),
    )
    wa = _wall_price(
        df[list(ASK_P)].to_numpy(dtype=float),
        df[list(ASK_V)].to_numpy(dtype=float),
    )
    return wa - wb


def _style_axes(ax: plt.Axes, title: str) -> None:
    ax.set_facecolor("#12151c")
    ax.set_title(title, color="#e8eaed", fontsize=13, fontweight="600", pad=10)
    ax.set_ylabel("Wall spread (ask wall - bid wall)", color="#9aa0a6", fontsize=10)
    ax.tick_params(colors="#9aa0a6", labelsize=9)
    ax.grid(True, alpha=0.22, color="#3c4043")
    for s in ax.spines.values():
        s.set_color("#3c4043")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))


def _plot_one(
    ax: plt.Axes,
    df: pd.DataFrame,
    title: str,
    color: str,
    show_x_labels: bool,
) -> None:
    ts = df["timestamp"].to_numpy()
    spread = wall_spread_series(df)
    ax.plot(ts, spread, color=color, linewidth=0.75, alpha=0.92)
    for x in DAY_BOUNDARIES:
        ax.axvline(x, color="#5f6368", linestyle="--", linewidth=0.8, alpha=0.85)
    med = float(np.nanmedian(spread))
    ax.axhline(med, color="#8ab4f8", linestyle=":", linewidth=1.0, alpha=0.8, label=f"median={med:,.1f}")
    ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor="#e8eaed")
    _style_axes(ax, title)
    if show_x_labels:
        ax.set_xticks(DAY_XTICKS, DAY_LABELS)
        ax.set_xlabel("Session (continuous timestamp)", color="#9aa0a6", fontsize=10)
    else:
        ax.set_xticklabels([])


def main() -> None:
    frames = load_round1_frames(ROOT)

    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0e14",
            "savefig.facecolor": "#0b0e14",
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica Neue", "DejaVu Sans", "Arial"],
        }
    )

    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"hspace": 0.28})
    fig.suptitle(
        f"ROUND {ROUND_NUM} - Wall spread (max-volume ask price - max-volume bid price), L1-L3",
        color="#e8eaed",
        fontsize=14,
        fontweight="700",
        y=0.98,
    )

    _plot_one(axes[0], frames.prices_ash, "ASH_COATED_OSMIUM", "#7cb7ff", show_x_labels=False)
    _plot_one(axes[1], frames.prices_pepper, "INTARIAN_PEPPER_ROOT", "#f0b429", show_x_labels=True)

    plt.subplots_adjust(bottom=0.1, top=0.9, left=0.08, right=0.97)
    fig.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
