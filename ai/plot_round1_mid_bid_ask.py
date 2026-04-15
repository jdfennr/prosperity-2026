"""Plot best bid, mid, and best ask for ROUND1 (+ trades); timestamp range via in-figure slider."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_paths import ROUND_NUM, TICK_OFFSET, Round1Frames, load_round1_frames  # noqa: E402

_OUT_DIR = Path(__file__).resolve().parent
OUT_MAIN_PNG = _OUT_DIR / f"round{ROUND_NUM}_mid_bid_ask.png"
OUT_MAIN_SVG = _OUT_DIR / f"round{ROUND_NUM}_mid_bid_ask.svg"
OUT_BY_DAY_PNG = _OUT_DIR / f"round{ROUND_NUM}_mid_bid_ask_by_day.png"
OUT_BY_DAY_SVG = _OUT_DIR / f"round{ROUND_NUM}_mid_bid_ask_by_day.svg"
SAVE_DPI = 220
# Continuous `timestamp` spans [0, 2_999_900] across three days (100 ticks/sec resolution).
TS_GLOBAL_MAX = 3 * TICK_OFFSET - 100

DAY_BOUNDARIES = (TICK_OFFSET, 2 * TICK_OFFSET)
DAY_LABELS = ("Day -2", "Day -1", "Day 0")
SESSION_DAYS: tuple[int, ...] = (-2, -1, 0)

# Trade bubbles: **diameter** ∝ quantity so e.g. qty 1 vs 10 → 1:10 linear size (area ∝ qty² in matplotlib `s`).
TRADE_DIAMETER_PX_PER_QTY = 3.4
TRADE_MARKER_AREA_PER_QTY = 7.5  # matplotlib `s` = (this * q)²


def _style_axes(ax: plt.Axes, title: str, ylabel: str) -> None:
    ax.set_facecolor("#12151c")
    ax.set_title(title, color="#e8eaed", fontsize=13, fontweight="600", pad=10)
    ax.set_ylabel(ylabel, color="#9aa0a6", fontsize=10)
    ax.tick_params(colors="#9aa0a6", labelsize=9)
    ax.grid(True, alpha=0.22, color="#3c4043")
    for s in ax.spines.values():
        s.set_color("#3c4043")


def clip_to_timestamp(
    df: pd.DataFrame,
    trades: pd.DataFrame,
    xmin: float | None,
    xmax: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[float, float]]:
    """Filter rows to ``timestamp`` in [xmin, xmax] (continuous session clock)."""
    ts = df["timestamp"]
    lo = float(ts.min() if xmin is None else xmin)
    hi = float(ts.max() if xmax is None else xmax)
    lo = max(lo, float(ts.min()))
    hi = min(hi, float(ts.max()))
    if lo > hi:
        lo, hi = hi, lo
    dm = (df["timestamp"] >= lo) & (df["timestamp"] <= hi)
    df2 = df.loc[dm].copy()
    if len(trades) > 0:
        tm = (trades["timestamp"] >= lo) & (trades["timestamp"] <= hi)
        tr2 = trades.loc[tm].copy()
    else:
        tr2 = trades
    return df2, tr2, (lo, hi)


def _legend_handles(*, markersize: float = 9.0) -> list[Patch | Line2D]:
    return [
        Patch(facecolor="#5cba8f", edgecolor="none", label="Bid (L1)"),
        Patch(facecolor="#e8eaed", edgecolor="none", label="Mid"),
        Patch(facecolor="#e8917a", edgecolor="none", label="Ask (L1)"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            linestyle="",
            markerfacecolor="#f4d03f",
            markeredgecolor="#2a2a2a",
            markeredgewidth=0.5,
            markersize=markersize,
            label="Trades (size ~ qty)",
        ),
    ]


def _trade_marker_sizes(quantity: pd.Series) -> np.ndarray:
    """Matplotlib scatter ``s`` (points²). Area ∝ qty² so **diameter** ∝ qty (match Plotly)."""
    q = quantity.to_numpy(dtype=float)
    d = TRADE_MARKER_AREA_PER_QTY * q
    s = d**2
    return np.clip(s, 6.0, 14_000.0)


def _plot_book(
    ax: plt.Axes,
    df: pd.DataFrame,
    trades: pd.DataFrame,
    title: str,
    show_x_labels: bool,
    *,
    x_time_col: str = "timestamp",
    show_day_dividers: bool = True,
    xlabel: str = "Session (continuous timestamp)",
    trade_alpha: float = 0.5,
    x_window: tuple[float, float] | None = None,
) -> None:
    ts = df[x_time_col].to_numpy()
    bid = df["bid_price_1"].to_numpy()
    ask = df["ask_price_1"].to_numpy()
    mid = df["mid_price"].to_numpy()
    mid_plot = np.where(mid == 0, np.nan, mid)

    ax.plot(ts, bid, color="#5cba8f", linewidth=0.9, label="Bid (L1)", alpha=0.95, zorder=2)
    ax.plot(ts, mid_plot, color="#e8eaed", linewidth=1.15, label="Mid", alpha=0.95, zorder=2)
    ax.plot(ts, ask, color="#e8917a", linewidth=0.9, label="Ask (L1)", alpha=0.95, zorder=2)

    tx = trades[x_time_col] if len(trades) else pd.Series(dtype=float)
    if len(trades) > 0:
        ax.scatter(
            tx,
            trades["price"],
            s=_trade_marker_sizes(trades["quantity"]),
            c="#f4d03f",
            edgecolors="#2a2a2a",
            linewidths=0.22,
            alpha=trade_alpha,
            zorder=6,
            rasterized=True,
        )

    if show_day_dividers:
        w_lo, w_hi = x_window if x_window is not None else (0.0, float(TS_GLOBAL_MAX))
        for x in DAY_BOUNDARIES:
            if w_lo <= x <= w_hi:
                ax.axvline(x, color="#5f6368", linestyle="--", linewidth=0.8, alpha=0.85)

    _style_axes(ax, title, "Price")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    if show_x_labels:
        if x_time_col == "timestamp":
            third = TICK_OFFSET / 3
            ax.set_xticks(
                [third, TICK_OFFSET + third, 2 * TICK_OFFSET + third],
                [DAY_LABELS[0], DAY_LABELS[1], DAY_LABELS[2]],
            )
        ax.set_xlabel(xlabel, color="#9aa0a6", fontsize=10)
    else:
        ax.set_xticklabels([])

    if x_window is not None and x_time_col == "timestamp":
        ax.set_xlim(x_window[0], x_window[1])


def plot_by_day_facets(
    frames: Round1Frames,
    *,
    suptitle: str,
) -> plt.Figure:
    """One column per simulation day — x is tick-in-day (readable scale)."""
    fig, axes = plt.subplots(
        2,
        3,
        figsize=(18, 10),
        sharex=True,
        gridspec_kw={"wspace": 0.22, "hspace": 0.32},
    )
    fig.patch.set_facecolor("#0b0e14")
    fig.suptitle(suptitle, color="#e8eaed", fontsize=14, fontweight="700", y=0.98)

    pairs: tuple[tuple[str, pd.DataFrame, pd.DataFrame], ...] = (
        ("ASH_COATED_OSMIUM", frames.prices_ash, frames.trades_ash),
        ("INTARIAN_PEPPER_ROOT", frames.prices_pepper, frames.trades_pepper),
    )

    for row, (name, px, tx) in enumerate(pairs):
        for col, day in enumerate(SESSION_DAYS):
            ax = axes[row, col]
            ddf = px[px["day"] == day].sort_values("timestamp_in_day")
            tdf = tx[tx["day"] == day].sort_values("timestamp_in_day")
            subt = f"{name}\nDay {day}"
            _plot_book(
                ax,
                ddf,
                tdf,
                subt,
                show_x_labels=(row == 1),
                x_time_col="timestamp_in_day",
                show_day_dividers=False,
                xlabel="Timestamp within day (same as simulator tick)",
                trade_alpha=0.5,
            )
            if row == 0:
                ax.set_xlabel("")

    fig.legend(
        handles=_legend_handles(markersize=8.0),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=4,
        frameon=False,
        labelcolor="#e8eaed",
        fontsize=9,
    )
    plt.subplots_adjust(bottom=0.12, top=0.91, left=0.06, right=0.98)
    return fig


def initial_timestamp_window(
    xmin: float | None,
    xmax: float | None,
) -> tuple[float, float]:
    lo0 = 0.0 if xmin is None else float(xmin)
    hi0 = 100_000.0 if xmax is None else float(xmax)
    lo0 = max(0.0, min(lo0, float(TS_GLOBAL_MAX)))
    hi0 = max(0.0, min(hi0, float(TS_GLOBAL_MAX)))
    if lo0 > hi0:
        lo0, hi0 = hi0, lo0
    return lo0, hi0


def draw_round1_mid_bid_ask_figure(
    frames: Round1Frames,
    lo: float,
    hi: float,
) -> plt.Figure:
    """Two stacked panels (ASH, Pepper) clipped to ``[lo, hi]`` on continuous ``timestamp``."""
    if lo > hi:
        lo, hi = hi, lo
    ash_c, ta_c, win = clip_to_timestamp(frames.prices_ash, frames.trades_ash, lo, hi)
    pep_c, tp_c, _ = clip_to_timestamp(frames.prices_pepper, frames.trades_pepper, lo, hi)

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(16, 9),
        sharex=True,
        gridspec_kw={"hspace": 0.28},
    )
    fig.patch.set_facecolor("#0b0e14")
    fig.suptitle(
        f"ROUND {ROUND_NUM} — timestamp [{win[0]:,.0f}, {win[1]:,.0f}]",
        color="#e8eaed",
        fontsize=14,
        fontweight="700",
        y=0.98,
    )
    _plot_book(
        axes[0],
        ash_c,
        ta_c,
        "ASH_COATED_OSMIUM",
        show_x_labels=False,
        x_window=win,
    )
    _plot_book(
        axes[1],
        pep_c,
        tp_c,
        "INTARIAN_PEPPER_ROOT",
        show_x_labels=True,
        x_window=win,
    )
    fig.legend(
        handles=_legend_handles(),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=4,
        frameon=False,
        labelcolor="#e8eaed",
        fontsize=10,
    )
    plt.subplots_adjust(bottom=0.12, top=0.9, left=0.07, right=0.97)
    return fig


def draw_round1_mid_bid_ask_plotly(
    frames: Round1Frames,
    lo: float,
    hi: float,
    *,
    trade_qty_min: float | None = None,
    trade_qty_max: float | None = None,
) -> go.Figure:
    """Interactive Plotly figure: hover shows **price** and **volume** (L1 book or trade qty).

    Trade markers are filtered to ``quantity ∈ [trade_qty_min, trade_qty_max]`` (inclusive).
    Use ``None`` for either bound to mean unbounded on that side (defaults: show all trades).
    """
    if lo > hi:
        lo, hi = hi, lo
    q_lo = -float("inf") if trade_qty_min is None else float(trade_qty_min)
    q_hi = float("inf") if trade_qty_max is None else float(trade_qty_max)
    if q_lo > q_hi:
        q_lo, q_hi = q_hi, q_lo

    ash_c, ta_c, win = clip_to_timestamp(frames.prices_ash, frames.trades_ash, lo, hi)
    pep_c, tp_c, _ = clip_to_timestamp(frames.prices_pepper, frames.trades_pepper, lo, hi)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"),
    )

    def add_panel(
        row: int,
        df: pd.DataFrame,
        trades: pd.DataFrame,
        *,
        show_legend: bool,
    ) -> None:
        if len(trades) > 0:
            qmask = (trades["quantity"] >= q_lo) & (trades["quantity"] <= q_hi)
            trades = trades.loc[qmask].copy()

        ts = df["timestamp"].to_numpy()
        bid = df["bid_price_1"].to_numpy()
        ask = df["ask_price_1"].to_numpy()
        bid_vol = df["bid_volume_1"].to_numpy()
        ask_vol = df["ask_volume_1"].to_numpy()
        mid = df["mid_price"].to_numpy(dtype=float)
        mid = np.where(mid == 0.0, np.nan, mid)

        fig.add_trace(
            go.Scatter(
                x=ts,
                y=bid,
                mode="lines",
                name="Bid (L1)",
                legendgroup="bid",
                line=dict(color="#5cba8f", width=1.1),
                customdata=bid_vol.reshape(-1, 1),
                hovertemplate=(
                    "<b>Bid (L1)</b><br>"
                    "timestamp=%{x:,.0f}<br>"
                    "price=%{y:,.2f}<br>"
                    "L1 volume=%{customdata[0]:,.0f}<extra></extra>"
                ),
                showlegend=show_legend,
            ),
            row=row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=ts,
                y=mid,
                mode="lines",
                name="Mid",
                legendgroup="mid",
                line=dict(color="#e8eaed", width=1.3),
                customdata=np.column_stack([bid_vol, ask_vol]),
                hovertemplate=(
                    "<b>Mid</b><br>"
                    "timestamp=%{x:,.0f}<br>"
                    "price=%{y:,.2f}<br>"
                    "bid L1 vol=%{customdata[0]:,.0f}<br>"
                    "ask L1 vol=%{customdata[1]:,.0f}<extra></extra>"
                ),
                connectgaps=False,
                showlegend=show_legend,
            ),
            row=row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=ts,
                y=ask,
                mode="lines",
                name="Ask (L1)",
                legendgroup="ask",
                line=dict(color="#e8917a", width=1.1),
                customdata=ask_vol.reshape(-1, 1),
                hovertemplate=(
                    "<b>Ask (L1)</b><br>"
                    "timestamp=%{x:,.0f}<br>"
                    "price=%{y:,.2f}<br>"
                    "L1 volume=%{customdata[0]:,.0f}<extra></extra>"
                ),
                showlegend=show_legend,
            ),
            row=row,
            col=1,
        )

        if len(trades) > 0:
            tx = trades["timestamp"].to_numpy()
            py = trades["price"].to_numpy()
            q = trades["quantity"].to_numpy(dtype=float)
            # `sizemode='diameter'`: marker.size is px diameter → linear ∝ qty (qty 1 vs 10 = 1:10).
            d_px = np.clip(TRADE_DIAMETER_PX_PER_QTY * q, 2.0, 95.0)
            fig.add_trace(
                go.Scatter(
                    x=tx,
                    y=py,
                    mode="markers",
                    name="Trades",
                    legendgroup="trades",
                    marker=dict(
                        size=d_px,
                        sizemode="diameter",
                        color="rgba(244,208,63,0.45)",
                        line=dict(width=0.35, color="rgba(32,32,32,0.55)"),
                    ),
                    customdata=q.reshape(-1, 1),
                    hovertemplate=(
                        "<b>Trade</b><br>"
                        "timestamp=%{x:,.0f}<br>"
                        "price=%{y:,.2f}<br>"
                        "quantity=%{customdata[0]:,.0f}<extra></extra>"
                    ),
                    showlegend=show_legend,
                ),
                row=row,
                col=1,
            )

        for bx in DAY_BOUNDARIES:
            if win[0] <= bx <= win[1]:
                fig.add_vline(
                    x=bx,
                    line_width=1,
                    line_dash="dash",
                    line_color="#5f6368",
                    row=row,
                    col=1,
                )

    add_panel(1, ash_c, ta_c, show_legend=True)
    add_panel(2, pep_c, tp_c, show_legend=False)

    qty_note = ""
    if trade_qty_min is not None or trade_qty_max is not None:
        lo_s = "−∞" if math.isinf(q_lo) and q_lo < 0 else f"{q_lo:g}"
        hi_s = "∞" if math.isinf(q_hi) and q_hi > 0 else f"{q_hi:g}"
        qty_note = (
            f"<br><span style='font-size:12px;font-weight:400'>"
            f"Trade markers: quantity ∈ [{lo_s}, {hi_s}]</span>"
        )

    fig.update_layout(
        title=dict(
            text=(
                f"ROUND {ROUND_NUM} — timestamp [{win[0]:,.0f}, {win[1]:,.0f}] "
                "<span style='font-size:12px;font-weight:400'>(hover traces for price & volume)</span>"
                f"{qty_note}"
            ),
            x=0.5,
            xanchor="center",
        ),
        paper_bgcolor="#0b0e14",
        plot_bgcolor="#12151c",
        font=dict(color="#e8eaed", size=11),
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(11,14,20,0.85)",
        ),
        height=880,
        margin=dict(l=64, r=28, t=100, b=56),
    )
    fig.update_xaxes(
        gridcolor="#3c4043",
        gridwidth=0.6,
        zeroline=False,
        showgrid=True,
        color="#9aa0a6",
        range=[win[0], win[1]],
    )
    fig.update_yaxes(
        gridcolor="#3c4043",
        gridwidth=0.6,
        zeroline=False,
        color="#9aa0a6",
        title=dict(text="Price", font=dict(size=12)),
    )
    fig.update_xaxes(title_text="Session (continuous timestamp)", row=2, col=1)

    third = TICK_OFFSET / 3
    tick_vals = [third, TICK_OFFSET + third, 2 * TICK_OFFSET + third]
    tick_text = list(DAY_LABELS)
    fig.update_xaxes(
        tickmode="array",
        tickvals=tick_vals,
        ticktext=tick_text,
        row=2,
        col=1,
    )

    return fig


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "ROUND1 mid/bid/ask + trades — batch export only. "
            "For the interactive UI: uv run streamlit run ai/streamlit_round1_mid_bid_ask.py"
        )
    )
    p.add_argument(
        "--xmin",
        type=float,
        default=None,
        help="Initial slider lower bound (default 0).",
    )
    p.add_argument(
        "--xmax",
        type=float,
        default=None,
        help="Initial slider upper bound (default 100000).",
    )
    p.add_argument(
        "--export",
        action="store_true",
        help="Save PNG/SVG at the window given by --xmin/--xmax (defaults 0–100000).",
    )
    p.add_argument(
        "--no-by-day",
        action="store_true",
        help="With --export: skip per-day facet charts.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.export:
        print("Interactive chart (smooth range slider + optional numeric inputs):")
        print("  uv run streamlit run ai/streamlit_round1_mid_bid_ask.py")
        print("Batch export still images:")
        print("  uv run python ai/plot_round1_mid_bid_ask.py --export")
        raise SystemExit(0)

    frames = load_round1_frames(ROOT)

    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0e14",
            "savefig.facecolor": "#0b0e14",
            "font.family": "sans-serif",
            "font.sans-serif": ["SF Pro Display", "Helvetica Neue", "DejaVu Sans", "Arial"],
        }
    )

    lo0, hi0 = initial_timestamp_window(args.xmin, args.xmax)
    fig = draw_round1_mid_bid_ask_figure(frames, lo0, hi0)
    fig.savefig(OUT_MAIN_PNG, dpi=SAVE_DPI, bbox_inches="tight")
    fig.savefig(OUT_MAIN_SVG, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT_MAIN_PNG} (dpi={SAVE_DPI})")
    print(f"Wrote {OUT_MAIN_SVG}")
    if not args.no_by_day:
        fig2 = plot_by_day_facets(
            frames,
            suptitle=(
                f"ROUND {ROUND_NUM} - Same data, one column per day "
                "(x = tick in day — easier to read trades & microstructure)"
            ),
        )
        fig2.savefig(OUT_BY_DAY_PNG, dpi=SAVE_DPI, bbox_inches="tight")
        fig2.savefig(OUT_BY_DAY_SVG, format="svg", bbox_inches="tight")
        plt.close(fig2)
        print(f"Wrote {OUT_BY_DAY_PNG}")
        print(f"Wrote {OUT_BY_DAY_SVG}")


if __name__ == "__main__":
    main()
