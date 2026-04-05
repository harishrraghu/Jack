import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator

from app.schemas import Candle


class IndicatorEngine:
    def calculate(self, candles: list[Candle]) -> dict[str, list[float]]:
        dataframe = pd.DataFrame([c.model_dump() for c in candles])
        close = dataframe["close"]
        high = dataframe["high"]
        low = dataframe["low"]
        volume = dataframe["volume"]

        ema21 = close.ewm(span=21, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()
        rsi14 = RSIIndicator(close=close, window=14).rsi().fillna(50.0)
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        adx = ADXIndicator(high=high, low=low, close=close, window=14).adx().fillna(0.0)
        tr = np.maximum.reduce(
            [
                high - low,
                (high - close.shift(1)).abs().fillna(0),
                (low - close.shift(1)).abs().fillna(0),
            ]
        )
        atr = pd.Series(tr).rolling(window=14).mean().bfill().fillna(0.0)

        return {
            "ema21": ema21.round(2).tolist(),
            "ema50": ema50.round(2).tolist(),
            "ema200": ema200.round(2).tolist(),
            "rsi14": rsi14.round(2).tolist(),
            "vwap": vwap.round(2).tolist(),
            "adx": adx.round(2).tolist(),
            "atr": atr.round(2).tolist(),
            "volume": volume.round(2).tolist(),
        }

