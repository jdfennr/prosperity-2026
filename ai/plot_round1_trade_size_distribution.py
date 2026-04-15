"""Distribution of trade sizes (executed quantity) per asset — ROUND1 merged trades."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_paths import ROUND_NUM, load_round1_frames  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / f"round{ROUND_NUM}_trade_size_distribution.png"
SAVE_DPI = 160


def _style_ax(ax: plt.Axes, title: str, xlabel: str) -> None:
    ax.set_facecolor("#12151c")
    ax.set_title(title, color="#e8eaed", fontsize=12, fontweight="600", pad=8)
    ax.set_xlabel(xlabel, color="#9aa0a6", fontsize=10)
    ax.set_ylabel("Number of trades", color="#9aa0a6", fontsize=10)
    ax.tick_params(colors="#9aa0a6", labelsize=9)
    ax.grid(True, alpha=0.22, color="#3c4043", axis="y")
    for s in ax.spines.values():
        s.set_color("#3c4043")


def main() -> None:
    frames = load_round1_frames(ROOT)
    pairs: tuple[tuple[str, pd.DataFrame, str], ...] = (
        ("ASH_COATED_OSMIUM", frames.trades_ash, "#5cba8f"),
        ("INTARIAN_PEPPER_ROOT", frames.trades_pepper, "#e8917a"),
    )

    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0e14",
            "savefig.facecolor": "#0b0e14",
            "font.family": "sans-serif",
            "font.sans-serif": ["SF Pro Display", "Helvetica Neue", "DejaVu Sans", "Arial"],
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"wspace": 0.28})
    fig.suptitle(
        f"ROUND {ROUND_NUM} — distribution of trade size (quantity per fill)",
        color="#e8eaed",
        fontsize=14,
        fontweight="700",
        y=1.02,
    )

    for ax, (name, tr, color) in zip(axes, pairs, strict=True):
        q = tr["quantity"].astype(float)
        vc = q.value_counts().sort_index()
        xs = vc.index.to_numpy(dtype=float)
        ys = vc.to_numpy(dtype=float)
        ax.bar(
            xs,
            ys,
            width=0.72,
            color=color,
            edgecolor="#0b0e14",
            linewidth=0.5,
            alpha=0.92,
        )
        n = int(len(tr))
        mx = float(q.max()) if len(q) else 0.0
        mean = float(q.mean()) if len(q) else float("nan")
        ax.set_xticks(xs)
        _style_ax(ax, f"{name}\n(n={n:,} trades, max size={mx:g})", "Trade quantity (units)")
        ax.text(
            0.98,
            0.97,
            f"mean = {mean:.3g}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="#8ab4f8",
        )

    plt.subplots_adjust(top=0.86, bottom=0.14, left=0.07, right=0.98)
    fig.savefig(OUT_PATH, dpi=SAVE_DPI, bbox_inches="tight")
    plt.close()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
