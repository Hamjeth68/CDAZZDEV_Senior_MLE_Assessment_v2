import numpy as np
import pandas as pd

from shared.indicators import (
    add_technical_indicators,
    bollinger_bands,
    derive_momentum_signal,
    latest_indicator_snapshot,
    rsi_wilder,
    simple_moving_average,
)


def test_simple_moving_average_waits_for_full_window() -> None:
    prices = pd.Series([1.0, 2.0, 3.0, 4.0])

    sma = simple_moving_average(prices, window=3)

    assert np.isnan(sma.iloc[1])
    assert sma.iloc[2] == 2.0
    assert sma.iloc[3] == 3.0


def test_rsi_wilder_handles_strong_uptrend_and_flat_prices() -> None:
    uptrend = pd.Series(range(1, 31), dtype=float)
    flat = pd.Series([10.0] * 30)

    assert rsi_wilder(uptrend, period=14).iloc[-1] == 100.0
    assert rsi_wilder(flat, period=14).iloc[-1] == 50.0


def test_bollinger_bands_match_rolling_mean_and_std() -> None:
    prices = pd.Series(range(1, 31), dtype=float)

    bands = bollinger_bands(prices, window=20, num_std=2)
    expected_middle = prices.iloc[-20:].mean()
    expected_std = prices.iloc[-20:].std()

    assert bands["bollinger_middle"].iloc[-1] == expected_middle
    assert bands["bollinger_upper"].iloc[-1] == expected_middle + (2 * expected_std)
    assert bands["bollinger_lower"].iloc[-1] == expected_middle - (2 * expected_std)


def test_add_technical_indicators_outputs_expected_columns_and_nulls() -> None:
    close = pd.Series(np.linspace(100.0, 150.0, 260))
    close.iloc[20] = np.nan
    prices = pd.DataFrame({"close": close})

    out = add_technical_indicators(prices)

    expected = {
        "sma_50",
        "sma_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bollinger_middle",
        "bollinger_upper",
        "bollinger_lower",
        "momentum_signal",
    }
    assert expected.issubset(out.columns)
    assert pd.isna(out["close"].iloc[20])
    assert out["sma_50"].iloc[-1] > out["sma_200"].iloc[-1]
    assert out["momentum_signal"].iloc[-1] in {"bullish", "bearish", "neutral"}


def test_momentum_signal_and_latest_snapshot_null_handling() -> None:
    assert derive_momentum_signal(pd.Series(dtype=float)) is None

    row = pd.Series({"sma_50": 110.0, "sma_200": 100.0, "rsi_14": 60.0, "macd": 2.0, "macd_signal": 1.0})
    assert derive_momentum_signal(row) == "bullish"

    snapshot = latest_indicator_snapshot(pd.DataFrame([{"sma_50": np.nan, "momentum_signal": None}]))
    assert snapshot.sma_50 is None
    assert snapshot.momentum_signal is None
