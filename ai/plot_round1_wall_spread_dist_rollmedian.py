"""Wall spread: histogram + rolling mean & median vs time (L1–L3 max-volume prices).

**Smoothing choices:** Rolling **mean** is cheap (O(n)), responds quickly, but follows outliers.
Rolling **median** is robust to spikes / discrete jumps but can look step-like when the raw
spread sits on a few levels. **EWMA** (exponential) is a good compromise online with one
halflife parameter—add if you want less lag than a long box window with smoother updates
than a short mean.
"""

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

from plot_round1_wall_spread import (  # noqa: E402
    DAY_BOUNDARIES,
    DAY_LABELS,
    DAY_XTICKS,
    wall_spread_series,
)
from repo_paths import ROUND_NUM, load_round1_frames  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / f"round{ROUND_NUM}_wall_spread_distribution_rollmedian.png"
SAVE_DPI = 160
ROLL_MEAN_TICKS = 500
ROLL_MEDIAN_TICKS = 2000


def _style_hist(ax: plt.Axes, title: str, xlabel: str) -> None:
    ax.set_facecolor("#12151c")
    ax.set_title(title, color="#e8eaed", fontsize=11, fontweight="600", pad=8)
    ax.set_xlabel(xlabel, color="#9aa0a6", fontsize=9)
    ax.set_ylabel("Count (ticks)", color="#9aa0a6", fontsize=9)
    ax.tick_params(colors="#9aa0a6", labelsize=8)
    ax.grid(True, alpha=0.22, color="#3c4043", axis="y")
    for s in ax.spines.values():
        s.set_color("#3c4043")


def _style_ts(ax: plt.Axes, title: str, ylabel: str) -> None:
    ax.set_facecolor("#12151c")
    ax.set_title(title, color="#e8eaed", fontsize=11, fontweight="600", pad=8)
    ax.set_ylabel(ylabel, color="#9aa0a6", fontsize=9)
    ax.tick_params(colors="#9aa0a6", labelsize=8)
    ax.grid(True, alpha=0.22, color="#3c4043")
    for s in ax.spines.values():
        s.set_color("#3c4043")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))


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

    fig, axes = plt.subplots(2, 2, figsize=(15, 9), gridspec_kw={"hspace": 0.35, "wspace": 0.28})
    fig.suptitle(
        f"ROUND {ROUND_NUM} — wall spread (max-vol ask − max-vol bid, L1–L3)\n"
        f"Distribution · rolling mean ({ROLL_MEAN_TICKS:,} ticks) & median ({ROLL_MEDIAN_TICKS:,} ticks)",
        color="#e8eaed",
        fontsize=12,
        fontweight="700",
        y=0.98,
    )

    pairs: tuple[tuple[str, pd.DataFrame, str], ...] = (
        ("ASH_COATED_OSMIUM", frames.prices_ash, "#7cb7ff"),
        ("INTARIAN_PEPPER_ROOT", frames.prices_pepper, "#f0b429"),
    )

    for col, (name, df, color) in enumerate(pairs):
        ts = df["timestamp"].to_numpy()
        spread = wall_spread_series(df)
        clean = np.asarray(spread, dtype=float)
        finite = np.isfinite(clean)

        ax_h = axes[0, col]
        data = clean[finite]
        ax_h.hist(
            data,
            bins=min(80, max(20, int(np.sqrt(len(data))))),
            color=color,
            edgecolor="#0b0e14",
            linewidth=0.35,
            alpha=0.92,
        )
        med = float(np.nanmedian(data))
        mean = float(np.nanmean(data))
        ax_h.axvline(med, color="#e8eaed", linestyle="--", linewidth=1.0, alpha=0.85, label=f"median={med:,.1f}")
        ax_h.axvline(mean, color="#8ab4f8", linestyle=":", linewidth=1.0, alpha=0.9, label=f"mean={mean:,.1f}")
        ax_h.legend(frameon=False, fontsize=7, loc="upper right", labelcolor="#e8eaed")
        _style_hist(ax_h, f"{name}", "Wall spread")

        ax_t = axes[1, col]
        ser = pd.Series(spread)
        roll_mean = ser.rolling(window=ROLL_MEAN_TICKS, min_periods=1).mean()
        roll_med = ser.rolling(window=ROLL_MEDIAN_TICKS, min_periods=1).median()
        ax_t.plot(
            ts,
            roll_mean.to_numpy(),
            color=color,
            linewidth=0.85,
            alpha=0.75,
            linestyle="-",
            label=f"{ROLL_MEAN_TICKS:,}-tick mean",
        )
        ax_t.plot(
            ts,
            roll_med.to_numpy(),
            color=color,
            linewidth=1.15,
            alpha=0.98,
            linestyle="--",
            label=f"{ROLL_MEDIAN_TICKS:,}-tick median",
        )
        ax_t.axhline(med, color="#5f6368", linestyle=":", linewidth=0.6, alpha=0.5)
        for x in DAY_BOUNDARIES:
            ax_t.axvline(x, color="#5f6368", linestyle="--", linewidth=0.75, alpha=0.75)
        ax_t.legend(
            frameon=False,
            fontsize=7,
            loc="upper left",
            labelcolor="#e8eaed",
        )
        _style_ts(
            ax_t,
            f"{name}",
            "Rolling spread (price units)",
        )
        ax_t.set_xticks(DAY_XTICKS, DAY_LABELS)
        ax_t.set_xlabel("Session (continuous timestamp)", color="#9aa0a6", fontsize=9)

    plt.subplots_adjust(top=0.88, bottom=0.14, left=0.07, right=0.98)
    fig.savefig(OUT_PATH, dpi=SAVE_DPI, bbox_inches="tight")
    plt.close()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
