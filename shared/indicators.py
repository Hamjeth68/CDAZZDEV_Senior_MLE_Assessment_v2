"""Technical indicators implemented from first principles with pandas/numpy."""

from __future__ import annotations

import numpy as np
import pandas as pd

from shared.schemas import TechnicalIndicatorSnapshot


def _as_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def simple_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate a simple moving average.

    Formula: ``SMA_t = mean(price[t-window+1 : t])``. Values before a full
    window is available are ``NaN`` so callers can distinguish insufficient
    history from a real zero.
    """
    return _as_numeric_series(series).rolling(window=window, min_periods=window).mean()


def rsi_wilder(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI using Wilder-style smoothing.

    RSI starts from average gains and losses over the first ``period`` price
    changes. Each following average is smoothed recursively:
    ``avg_gain_t = (avg_gain_{t-1} * (period - 1) + gain_t) / period`` and the
    same formula is used for losses. ``RS = avg_gain / avg_loss`` and
    ``RSI = 100 - (100 / (1 + RS))``.
    """
    prices = _as_numeric_series(series)
    delta = prices.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)

    rsi = pd.Series(np.nan, index=prices.index, dtype=float)
    valid_changes = delta.dropna()
    if len(valid_changes) < period:
        return rsi

    avg_gain = gains.iloc[1 : period + 1].mean(skipna=True)
    avg_loss = losses.iloc[1 : period + 1].mean(skipna=True)

    def score(gain_avg: float, loss_avg: float) -> float:
        if np.isclose(loss_avg, 0.0) and np.isclose(gain_avg, 0.0):
            return 50.0
        if np.isclose(loss_avg, 0.0):
            return 100.0
        if np.isclose(gain_avg, 0.0):
            return 0.0
        rs = gain_avg / loss_avg
        return 100.0 - (100.0 / (1.0 + rs))

    rsi.iloc[period] = score(avg_gain, avg_loss)

    for i in range(period + 1, len(prices)):
        gain = gains.iloc[i]
        loss = losses.iloc[i]
        if pd.isna(gain) or pd.isna(loss):
            continue
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        rsi.iloc[i] = score(avg_gain, avg_loss)

    return rsi


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Calculate MACD and its signal line.

    Formula: ``MACD = EMA_fast(price) - EMA_slow(price)`` using spans 12 and 26
    by default. The signal line is a 9-period EMA of MACD, and the histogram is
    ``MACD - signal``.
    """
    prices = _as_numeric_series(series)
    ema_fast = prices.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = prices.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()

    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": macd_line - signal_line,
        },
        index=prices.index,
    )


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Calculate Bollinger Bands.

    Formula: the middle band is the ``window``-period SMA. The upper band is
    ``middle + num_std * rolling_std`` and the lower band is
    ``middle - num_std * rolling_std``. The standard deviation uses pandas'
    sample standard deviation, matching common charting defaults.
    """
    prices = _as_numeric_series(series)
    middle = simple_moving_average(prices, window)
    rolling_std = prices.rolling(window=window, min_periods=window).std()

    return pd.DataFrame(
        {
            "bollinger_middle": middle,
            "bollinger_upper": middle + (num_std * rolling_std),
            "bollinger_lower": middle - (num_std * rolling_std),
        },
        index=prices.index,
    )


def derive_momentum_signal(row: pd.Series) -> str | None:
    """Derive a coarse momentum label from SMA trend, RSI, and MACD.

    The signal votes bullish when 50-day SMA is above 200-day SMA, RSI is above
    55, or MACD is above its signal line. It votes bearish for the inverse
    conditions: 50-day SMA below 200-day SMA, RSI below 45, or MACD below signal.
    Two or more aligned votes produce ``"bullish"`` or ``"bearish"``;
    otherwise the result is ``"neutral"``. If every input is missing, ``None``
    is returned.
    """
    bullish = 0
    bearish = 0
    observed = 0

    sma_50 = row.get("sma_50")
    sma_200 = row.get("sma_200")
    if pd.notna(sma_50) and pd.notna(sma_200):
        observed += 1
        bullish += int(sma_50 > sma_200)
        bearish += int(sma_50 < sma_200)

    rsi = row.get("rsi_14")
    if pd.notna(rsi):
        observed += 1
        bullish += int(rsi > 55.0)
        bearish += int(rsi < 45.0)

    macd_value = row.get("macd")
    macd_signal = row.get("macd_signal")
    if pd.notna(macd_value) and pd.notna(macd_signal):
        observed += 1
        bullish += int(macd_value > macd_signal)
        bearish += int(macd_value < macd_signal)

    if observed == 0:
        return None
    if bullish >= 2 and bullish > bearish:
        return "bullish"
    if bearish >= 2 and bearish > bullish:
        return "bearish"
    return "neutral"


def add_technical_indicators(prices: pd.DataFrame, price_column: str = "close") -> pd.DataFrame:
    """Return a copy of ``prices`` with core technical indicators appended.

    Adds 50-day SMA, 200-day SMA, 14-period Wilder RSI, MACD 12/26/9,
    Bollinger Bands 20/2, and a momentum signal derived from SMA/RSI/MACD.
    Missing close values are coerced to ``NaN`` and propagate through the
    rolling calculations rather than raising.
    """
    if price_column not in prices.columns:
        raise ValueError(f"prices must include a '{price_column}' column")

    out = prices.copy()
    close = _as_numeric_series(out[price_column])
    out[price_column] = close

    out["sma_50"] = simple_moving_average(close, 50)
    out["sma_200"] = simple_moving_average(close, 200)
    out["rsi_14"] = rsi_wilder(close, 14)
    out = out.join(macd(close))
    out = out.join(bollinger_bands(close))
    out["momentum_signal"] = out.apply(derive_momentum_signal, axis=1)

    return out


def latest_indicator_snapshot(indicators: pd.DataFrame) -> TechnicalIndicatorSnapshot:
    """Build a schema snapshot from the latest available indicator row."""
    if indicators.empty:
        return TechnicalIndicatorSnapshot()

    snapshot_columns = [
        "sma_50",
        "sma_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "bollinger_upper",
        "bollinger_lower",
        "momentum_signal",
    ]
    available_columns = [column for column in snapshot_columns if column in indicators.columns]
    if not available_columns:
        return TechnicalIndicatorSnapshot()

    populated_mask = indicators[available_columns].notna().any(axis=1)
    if not populated_mask.any():
        return TechnicalIndicatorSnapshot()

    row = indicators.loc[populated_mask].iloc[-1]

    def clean(value: object) -> float | None:
        if pd.isna(value):
            return None
        return float(value)

    signal = row.get("momentum_signal")
    if pd.isna(signal):
        signal = None

    return TechnicalIndicatorSnapshot(
        sma_50=clean(row.get("sma_50")),
        sma_200=clean(row.get("sma_200")),
        rsi_14=clean(row.get("rsi_14")),
        macd=clean(row.get("macd")),
        macd_signal=clean(row.get("macd_signal")),
        bollinger_upper=clean(row.get("bollinger_upper")),
        bollinger_lower=clean(row.get("bollinger_lower")),
        momentum_signal=signal,
    )
