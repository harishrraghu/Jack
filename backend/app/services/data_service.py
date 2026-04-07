from pathlib import Path

import pandas as pd

from app.schemas import Candle


class DataService:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parents[2]
        self.data_dir = self.base_dir / "data"
        self.sample_path = self.data_dir / "sample" / "banknifty_15m.csv"
        self.intraday_candidates = [
            self.data_dir / "banknifty_15m_merged.csv",
            self.data_dir / "banknifty_15m_recent.csv",
            self.data_dir / "banknifty_15m.csv",
            self.sample_path,
        ]
        self.daily_path = self.data_dir / "banknifty_daily.csv"

    def _resolve_intraday_path(self) -> Path:
        for path in self.intraday_candidates:
            if path.exists():
                return path
        return self.sample_path

    def _load_csv(self, path: Path) -> pd.DataFrame:
        dataframe = pd.read_csv(path)
        dataframe.columns = [str(column).strip().lower() for column in dataframe.columns]
        expected_columns = ["time", "open", "high", "low", "close", "volume"]
        missing = [column for column in expected_columns if column not in dataframe.columns]
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

        for column in expected_columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        dataframe = dataframe.dropna(subset=["time", "open", "high", "low", "close"]).copy()
        dataframe["time"] = dataframe["time"].astype("int64")
        dataframe["volume"] = dataframe["volume"].fillna(0.0)
        return dataframe[expected_columns].sort_values("time").reset_index(drop=True)

    def _aggregate_daily(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        frame = dataframe.copy()
        frame["datetime"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
        frame["session_date"] = frame["datetime"].dt.normalize()
        daily = (
            frame.groupby("session_date", sort=True)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
        daily["time"] = (daily["session_date"].astype("int64") // 10**9).astype("int64")
        return daily[["time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)

    def _expand_to_5m(self, dataframe: pd.DataFrame, limit: int) -> pd.DataFrame:
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
        return pd.DataFrame(expanded).tail(limit).reset_index(drop=True)

    async def get_candles(self, timeframe: str) -> list[Candle]:
        dataframe = self._load_csv(self._resolve_intraday_path())
        limit = {"5m": 80, "15m": 100, "1d": 60}.get(timeframe, 100)

        if timeframe == "1d":
            return await self.get_daily_candles(lookback_days=limit)
        elif timeframe == "5m":
            dataframe = self._expand_to_5m(dataframe.tail(40).reset_index(drop=True), limit)
        else:
            dataframe = dataframe.tail(limit).reset_index(drop=True)

        return [Candle(**row) for row in dataframe.to_dict(orient="records")]

    async def get_daily_candles(self, lookback_days: int = 5) -> list[Candle]:
        if self.daily_path.exists():
            dataframe = self._load_csv(self.daily_path)
        else:
            dataframe = self._aggregate_daily(self._load_csv(self._resolve_intraday_path()))

        dataframe = dataframe.tail(lookback_days).reset_index(drop=True)
        return [Candle(**row) for row in dataframe.to_dict(orient="records")]

    async def get_global_context(self) -> dict:
        daily = await self.get_daily_candles(lookback_days=2)
        if not daily:
            return {
                "gift_nifty_delta": 0.0,
                "event_risk": False,
                "options_pcr": 1.0,
                "oi_wall_above": 0.0,
                "oi_wall_below": 0.0,
            }

        prev_day = daily[-2] if len(daily) >= 2 else daily[-1]
        day_range = prev_day.high - prev_day.low
        return {
            "gift_nifty_delta": 0.0,
            "event_risk": False,
            "options_pcr": 1.0,
            "oi_wall_above": prev_day.high + day_range * 0.5,
            "oi_wall_below": prev_day.low - day_range * 0.5,
        }
