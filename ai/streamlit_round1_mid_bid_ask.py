"""ROUND1 mid/bid/ask + trades — Streamlit UI with range slider and Plotly hovers (price & volume)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from plotly.io import to_image

_AI_DIR = Path(__file__).resolve().parent
ROOT = _AI_DIR.parent
for _p in (ROOT, _AI_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from plot_round1_mid_bid_ask import (  # noqa: E402
    ROUND_NUM,
    TS_GLOBAL_MAX,
    draw_round1_mid_bid_ask_plotly,
)
from repo_paths import load_round1_frames  # noqa: E402

_SLIDER_KEY = "main_ts_range_slider"
_DEFAULT_RANGE: tuple[float, float] = (0.0, 100_000.0)
_QTY_SLIDER_KEY = "trade_qty_range_slider"


@st.cache_data(show_spinner="Loading ROUND1 data…")
def _load_frames():
    return load_round1_frames(ROOT)


def main() -> None:
    st.set_page_config(
        page_title=f"ROUND {ROUND_NUM} mid/bid/ask",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if _SLIDER_KEY not in st.session_state:
        st.session_state[_SLIDER_KEY] = _DEFAULT_RANGE

    st.title(f"ROUND {ROUND_NUM} — mid / bid / ask + trades")
    st.caption(
        f"Continuous session `timestamp` ∈ [0, {TS_GLOBAL_MAX:,.0f}]. "
        "Hover any line or trade marker for **price** and **volume** (L1 book depth or trade size)."
    )

    frames = _load_frames()

    tq = pd.concat(
        [frames.trades_ash["quantity"], frames.trades_pepper["quantity"]],
        ignore_index=True,
    )
    qmin_d = float(tq.min())
    qmax_d = float(tq.max())
    if qmax_d <= qmin_d:
        qmax_d = qmin_d + 1.0

    if _QTY_SLIDER_KEY not in st.session_state:
        st.session_state[_QTY_SLIDER_KEY] = (qmin_d, qmax_d)

    lo_cur, hi_cur = st.session_state[_SLIDER_KEY]

    with st.sidebar:
        st.header("Numeric bounds")
        with st.form("numeric_window"):
            lo_in = st.number_input(
                "Min timestamp",
                min_value=0.0,
                max_value=float(TS_GLOBAL_MAX),
                value=float(lo_cur),
                step=100.0,
                format="%.0f",
            )
            hi_in = st.number_input(
                "Max timestamp",
                min_value=0.0,
                max_value=float(TS_GLOBAL_MAX),
                value=float(hi_cur),
                step=100.0,
                format="%.0f",
            )
            if st.form_submit_button("Apply"):
                lo_f, hi_f = float(lo_in), float(hi_in)
                if lo_f > hi_f:
                    lo_f, hi_f = hi_f, lo_f
                st.session_state[_SLIDER_KEY] = (lo_f, hi_f)
                st.rerun()

        st.divider()
        st.caption("Sidebar values update the main range slider.")

        st.subheader("Trade size (markers)")
        st.slider(
            "Quantity range (yellow circles only)",
            min_value=qmin_d,
            max_value=qmax_d,
            value=st.session_state[_QTY_SLIDER_KEY],
            step=1.0,
            key=_QTY_SLIDER_KEY,
            help="Filter trade markers by order size, e.g. cap at 9 to hide size ≥ 10.",
        )

    st.slider(
        "Timestamp range",
        0.0,
        float(TS_GLOBAL_MAX),
        step=100.0,
        format="%d",
        key=_SLIDER_KEY,
        help="Drag handles or click the track. The chart below uses Plotly — hover traces for details.",
    )

    win = st.session_state[_SLIDER_KEY]
    lo, hi = float(win[0]), float(win[1])
    if lo > hi:
        lo, hi = hi, lo

    q_lo, q_hi = st.session_state[_QTY_SLIDER_KEY]
    q_lo, q_hi = float(q_lo), float(q_hi)
    if q_lo > q_hi:
        q_lo, q_hi = q_hi, q_lo

    st.markdown(f"**Active window:** `{lo:,.0f}` → `{hi:,.0f}`  ·  **Trade qty:** `{q_lo:g}` → `{q_hi:g}`")

    fig = draw_round1_mid_bid_ask_plotly(
        frames,
        lo,
        hi,
        trade_qty_min=q_lo,
        trade_qty_max=q_hi,
    )
    st.plotly_chart(fig, use_container_width=True)

    try:
        png_bytes = to_image(fig, format="png", engine="kaleido", scale=2)
    except Exception as exc:  # noqa: BLE001 — surface kaleido/config issues in UI
        st.caption(f"PNG export unavailable ({exc!s}).")
    else:
        st.download_button(
            label="Download PNG (current window)",
            data=png_bytes,
            file_name=(
                f"round{ROUND_NUM}_mid_bid_ask_{int(lo)}_{int(hi)}_"
                f"qty_{int(round(q_lo))}_{int(round(q_hi))}.png"
            ),
            mime="image/png",
        )


if __name__ == "__main__":
    main()
