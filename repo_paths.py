"""Project root path and ROUND1 merge helpers (raw day CSVs → four in-memory DataFrames)."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pandas as pd

ROUND_NUM = 1
DAY_ORDER: tuple[int, ...] = (-2, -1, 0)
TICK_OFFSET = 1_000_000


def repo_root() -> Path:
    """This repository: directory containing ``pyproject.toml`` (same folder as this file)."""
    return Path(__file__).resolve().parent


def round1_raw_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "src/data/ROUND1/raw"


class Round1Frames(NamedTuple):
    prices_ash: pd.DataFrame
    prices_pepper: pd.DataFrame
    trades_ash: pd.DataFrame
    trades_pepper: pd.DataFrame


def _day_index(day: int) -> int:
    return DAY_ORDER.index(day)


def _load_prices_merged(raw: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for day in DAY_ORDER:
        path = raw / f"prices_round_{ROUND_NUM}_day_{day}.csv"
        frames.append(pd.read_csv(path, sep=";"))
    out = pd.concat(frames, ignore_index=True)
    out["timestamp_in_day"] = out["timestamp"]
    out["timestamp"] = out["timestamp_in_day"] + out["day"].map(_day_index) * TICK_OFFSET
    return out


def _load_trades_merged(raw: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for day in DAY_ORDER:
        df = pd.read_csv(raw / f"trades_round_{ROUND_NUM}_day_{day}.csv", sep=";")
        df.insert(0, "day", day)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["timestamp_in_day"] = out["timestamp"]
    out["timestamp"] = out["timestamp_in_day"] + out["day"].map(_day_index) * TICK_OFFSET
    return out


def load_round1_frames(root: Path | None = None) -> Round1Frames:
    """Merge ROUND1 raw day files into four DataFrames (continuous timestamp, sorted)."""
    raw = round1_raw_dir(root)
    prices = _load_prices_merged(raw)
    trades = _load_trades_merged(raw)

    ash_p = (
        prices[prices["product"] == "ASH_COATED_OSMIUM"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    pep_p = (
        prices[prices["product"] == "INTARIAN_PEPPER_ROOT"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    ash_t = (
        trades[trades["symbol"] == "ASH_COATED_OSMIUM"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    pep_t = (
        trades[trades["symbol"] == "INTARIAN_PEPPER_ROOT"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    return Round1Frames(ash_p, pep_p, ash_t, pep_t)
