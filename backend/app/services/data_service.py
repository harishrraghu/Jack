from pathlib import Path

import pandas as pd

from app.schemas import Candle


class DataService:
    def __init__(self) -> None:
        self.sample_path = Path("data/sample/banknifty_15m.csv")

    async def get_candles(self, timeframe: str) -> list[Candle]:
        dataframe = pd.read_csv(self.sample_path)
        limit = {"5m": 80, "15m": 100, "1d": 60}.get(timeframe, 100)
        dataframe = dataframe.tail(limit).reset_index(drop=True)

        if timeframe == "1d":
            dataframe = (
                dataframe.assign(date=pd.to_datetime(dataframe["time"], unit="s"))
                .set_index("date")
                .resample("1D")
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
                .dropna()
                .reset_index()
            )
            dataframe["time"] = dataframe["date"].astype("int64") // 10**9
            dataframe = dataframe.drop(columns=["date"])
        elif timeframe == "5m":
            expanded = []
            for _, row in dataframe.iterrows():
                spread = (row["close"] - row["open"]) / 3
                for step in range(3):
                    expanded.append(
                        {
                            "time": int(row["time"] - (2 - step) * 300),
                            "open": float(row["open"] + spread * step),
                            "high": float(max(row["high"], row["open"] + spread * (step + 1))),
                            "low": float(min(row["low"], row["open"] + spread * step)),
                            "close": float(row["open"] + spread * (step + 1)),
                            "volume": float(row["volume"] / 3),
                        }
                    )
            dataframe = pd.DataFrame(expanded).tail(limit).reset_index(drop=True)

        return [Candle(**row) for row in dataframe.to_dict(orient="records")]

    async def get_global_context(self) -> dict:
        return {
            "gift_nifty_delta": 0.42,
            "event_risk": False,
            "options_pcr": 1.08,
            "oi_wall_above": 52150,
            "oi_wall_below": 51600,
        }

