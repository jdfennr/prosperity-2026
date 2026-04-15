"""Cumulative signed trade imbalance for ASH: bid-side +qty, ask-side −qty (tick-aligned cumsum)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_paths import ROUND_NUM, TICK_OFFSET, load_round1_frames  # noqa: E402

DAY_BOUNDARIES = (TICK_OFFSET, 2 * TICK_OFFSET)
DAY_LABELS = ("Day -2", "Day -1", "Day 0")

OUT_PATH = Path(__file__).resolve().parent / f"round{ROUND_NUM}_ash_trade_imbalance_cumulative.png"
SAVE_DPI = 160


def _signed_trade_qty(
    price: np.ndarray,
    bid: np.ndarray,
    ask: np.ndarray,
    mid: np.ndarray,
    qty: np.ndarray,
) -> np.ndarray:
    """+quantity if trade is priced at/near bid; −quantity if at/near ask (see inside-spread rule)."""
    out = np.zeros(len(price), dtype=float)
    valid = np.isfinite(bid) & np.isfinite(ask)
    at_bid = valid & (price <= bid)
    at_ask = valid & (price >= ask)
    inside = valid & (price > bid) & (price < ask)
    out[at_bid] = qty[at_bid]
    out[at_ask] = -qty[at_ask]
    mid_ok = inside & np.isfinite(mid) & (mid > 0)
    out[mid_ok & (price < mid)] = qty[mid_ok & (price < mid)]
    out[mid_ok & (price > mid)] = -qty[mid_ok & (price > mid)]
    # price == mid or empty book: leave 0
    return out


def main() -> None:
    frames = load_round1_frames(ROOT)
    px = frames.prices_ash.sort_values("timestamp").reset_index(drop=True)
    tr = frames.trades_ash

    book = px[["timestamp", "bid_price_1", "ask_price_1", "mid_price"]]
    m = tr.merge(book, on="timestamp", how="left")

    m["signed_qty"] = _signed_trade_qty(
        m["price"].to_numpy(dtype=float),
        m["bid_price_1"].to_numpy(dtype=float),
        m["ask_price_1"].to_numpy(dtype=float),
        m["mid_price"].to_numpy(dtype=float),
        m["quantity"].to_numpy(dtype=float),
    )

    per_ts = m.groupby("timestamp", sort=True)["signed_qty"].sum()
    timeline = px["timestamp"].to_numpy()
    tick_imb = per_ts.reindex(timeline, fill_value=0.0)
    cumulative = tick_imb.cumsum()

    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0e14",
            "savefig.facecolor": "#0b0e14",
            "font.family": "sans-serif",
            "font.sans-serif": ["SF Pro Display", "Helvetica Neue", "DejaVu Sans", "Arial"],
        }
    )

    fig, (ax_p, ax_r) = plt.subplots(
        2,
        1,
        figsize=(14, 8.5),
        sharex=True,
        gridspec_kw={"height_ratios": [1.15, 1.0], "hspace": 0.12},
    )
    fig.patch.set_facecolor("#0b0e14")
    for ax in (ax_p, ax_r):
        ax.set_facecolor("#12151c")
        ax.tick_params(colors="#9aa0a6", labelsize=9)
        ax.grid(True, alpha=0.22, color="#3c4043")
        for s in ax.spines.values():
            s.set_color("#3c4043")

    bid = px["bid_price_1"].to_numpy(dtype=float)
    ask = px["ask_price_1"].to_numpy(dtype=float)
    mid = px["mid_price"].to_numpy(dtype=float)
    mid_plot = np.where(mid == 0.0, np.nan, mid)

    ax_p.plot(timeline, bid, color="#5cba8f", linewidth=0.85, label="Bid (L1)", alpha=0.95, zorder=2)
    ax_p.plot(timeline, mid_plot, color="#e8eaed", linewidth=1.05, label="Mid", alpha=0.95, zorder=2)
    ax_p.plot(timeline, ask, color="#e8917a", linewidth=0.85, label="Ask (L1)", alpha=0.95, zorder=2)
    for x in DAY_BOUNDARIES:
        ax_p.axvline(x, color="#5f6368", linestyle="--", linewidth=0.75, alpha=0.85)
    ax_p.set_ylabel("Price", color="#9aa0a6", fontsize=10)
    ax_p.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax_p.legend(loc="upper right", frameon=False, fontsize=8, labelcolor="#e8eaed")
    ax_p.tick_params(axis="x", labelbottom=False)
    ax_p.set_title(
        "L1 bid / mid / ask",
        color="#e8eaed",
        fontsize=11,
        fontweight="600",
        pad=8,
    )

    ax_r.plot(timeline, cumulative.to_numpy(), color="#5cba8f", linewidth=0.9, alpha=0.95)
    ax_r.axhline(0.0, color="#5f6368", linestyle="--", linewidth=0.8, alpha=0.9)
    for x in DAY_BOUNDARIES:
        ax_r.axvline(x, color="#5f6368", linestyle="--", linewidth=0.75, alpha=0.85)
    ax_r.set_xlabel("Session (continuous timestamp)", color="#9aa0a6", fontsize=10)
    ax_r.set_ylabel(
        "Cumulative signed quantity (session)",
        color="#9aa0a6",
        fontsize=10,
    )
    ax_r.set_title(
        "Bid-side +qty · Ask-side −qty · Inside spread vs mid",
        color="#9aa0a6",
        fontsize=9,
        pad=6,
    )
    third = TICK_OFFSET / 3
    ax_r.set_xticks(
        [third, TICK_OFFSET + third, 2 * TICK_OFFSET + third],
        list(DAY_LABELS),
    )

    fig.suptitle(
        f"ROUND {ROUND_NUM} — ASH_COATED_OSMIUM",
        color="#e8eaed",
        fontsize=13,
        fontweight="700",
        y=0.98,
    )

    plt.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.08)
    fig.savefig(OUT_PATH, dpi=SAVE_DPI, bbox_inches="tight")
    plt.close()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
