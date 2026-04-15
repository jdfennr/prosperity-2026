"""Per-tick distributions of total bid volume and total ask volume (3 levels summed)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_paths import ROUND_NUM, load_round1_frames  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / f"round{ROUND_NUM}_volume_distributions.png"

BID_VOL_COLS = ("bid_volume_1", "bid_volume_2", "bid_volume_3")
ASK_VOL_COLS = ("ask_volume_1", "ask_volume_2", "ask_volume_3")


def _total_bid_vol(df: pd.DataFrame) -> pd.Series:
    return df[list(BID_VOL_COLS)].sum(axis=1, skipna=True)


def _total_ask_vol(df: pd.DataFrame) -> pd.Series:
    return df[list(ASK_VOL_COLS)].sum(axis=1, skipna=True)


def _style_ax(ax: plt.Axes, title: str, xlabel: str) -> None:
    ax.set_facecolor("#12151c")
    ax.set_title(title, color="#e8eaed", fontsize=12, fontweight="600", pad=8)
    ax.set_xlabel(xlabel, color="#9aa0a6", fontsize=10)
    ax.set_ylabel("Count (ticks)", color="#9aa0a6", fontsize=10)
    ax.tick_params(colors="#9aa0a6", labelsize=9)
    ax.grid(True, alpha=0.22, color="#3c4043", axis="y")
    for s in ax.spines.values():
        s.set_color("#3c4043")


def main() -> None:
    frames = load_round1_frames(ROOT)
    pairs: list[tuple[str, pd.DataFrame]] = [
        ("ASH_COATED_OSMIUM", frames.prices_ash),
        ("INTARIAN_PEPPER_ROOT", frames.prices_pepper),
    ]

    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0e14",
            "savefig.facecolor": "#0b0e14",
            "font.family": "sans-serif",
            "font.sans-serif": ["SF Pro Display", "Helvetica Neue", "DejaVu Sans", "Arial"],
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), gridspec_kw={"hspace": 0.35, "wspace": 0.28})
    fig.suptitle(
        f"ROUND {ROUND_NUM} - Distribution of total book volume per tick (L1+L2+L3, all days)",
        color="#e8eaed",
        fontsize=14,
        fontweight="700",
        y=0.98,
    )

    for row, (sym, df) in enumerate(pairs):
        bid_v = _total_bid_vol(df)
        ask_v = _total_ask_vol(df)

        for col, (series, side, color) in enumerate(
            [
                (bid_v, "Bid volume", "#5cba8f"),
                (ask_v, "Ask volume", "#e8917a"),
            ]
        ):
            ax = axes[row, col]
            data = series.replace([np.inf, -np.inf], np.nan).dropna()
            ax.hist(
                data,
                bins=55,
                color=color,
                edgecolor="#0b0e14",
                linewidth=0.35,
                alpha=0.92,
            )
            med = float(data.median())
            mean = float(data.mean())
            ax.axvline(med, color="#e8eaed", linestyle="--", linewidth=1.1, alpha=0.85, label=f"median={med:.1f}")
            ax.axvline(mean, color="#8ab4f8", linestyle=":", linewidth=1.0, alpha=0.9, label=f"mean={mean:.1f}")
            ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor="#e8eaed")
            _style_ax(
                ax,
                f"{sym} - {side}",
                "Total volume (units) at this tick",
            )

    plt.subplots_adjust(top=0.9, bottom=0.08, left=0.08, right=0.97)
    fig.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
