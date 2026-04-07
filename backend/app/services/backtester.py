from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import AsyncIterator, Literal
from zoneinfo import ZoneInfo

import pandas as pd

from app.schemas import AnalysisResponse, Candle, ForecastResult
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.forecast_service import ForecastService

IST = "Asia/Kolkata"
IST_ZONE = ZoneInfo(IST)


@dataclass
class BacktestTrade:
    direction: Literal["BUY_CALL", "BUY_PUT"]
    entry_spot: float
    entry_option_price: float
    spot_stop_loss: float
    spot_target: float
    entry_time: int
    quantity: int = 15


class PortfolioManager:
    def __init__(self, starting_capital: float = 10_000.0) -> None:
        self.starting_capital = starting_capital
        self.capital = starting_capital
        self.day_pnl = 0.0
        self.realized_pnl = 0.0
        self.total_fees = 0.0
        self.trades_count = 0

    def _calculate_fees(self, sell_premium_total: float) -> dict[str, float]:
        brokerage = 40.0
        stt = 0.00125 * sell_premium_total
        exchange_txn = 0.0005 * sell_premium_total
        gst = 0.18 * (brokerage + exchange_txn)
        total = brokerage + stt + exchange_txn + gst
        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "exchange_txn": round(exchange_txn, 2),
            "gst": round(gst, 2),
            "total": round(total, 2),
        }

    def settle_trade(
        self,
        trade: BacktestTrade,
        exit_spot: float,
        exit_time: int,
        reason: str,
    ) -> dict:
        spot_move = exit_spot - trade.entry_spot
        if trade.direction == "BUY_PUT":
            spot_move *= -1
        option_move = spot_move * 0.5
        exit_option_price = max(0.05, trade.entry_option_price + option_move)

        gross_pnl = (exit_option_price - trade.entry_option_price) * trade.quantity
        sell_premium_total = exit_option_price * trade.quantity
        fees = self._calculate_fees(sell_premium_total)
        net_pnl = gross_pnl - fees["total"]

        self.capital += net_pnl
        self.day_pnl += net_pnl
        self.realized_pnl += net_pnl
        self.total_fees += fees["total"]
        self.trades_count += 1

        return {
            "entry_time": trade.entry_time,
            "exit_time": exit_time,
            "direction": trade.direction,
            "entry_spot": round(trade.entry_spot, 2),
            "exit_spot": round(exit_spot, 2),
            "entry_option_price": round(trade.entry_option_price, 2),
            "exit_option_price": round(exit_option_price, 2),
            "quantity": trade.quantity,
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "fees": fees,
            "reason": reason,
        }

    def snapshot(self) -> dict:
        return {
            "starting_capital": round(self.starting_capital, 2),
            "capital": round(self.capital, 2),
            "day_pnl": round(self.day_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_fees": round(self.total_fees, 2),
            "trades_count": self.trades_count,
        }


class MultiTimeframeBacktestLoader:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.base_dir = Path(__file__).resolve().parents[2]
        root_data_dir = self.base_dir / "data"
        self.data_dir = data_dir or root_data_dir / "archive"
        self.paths = {
            "15m": self.data_dir / "bank-nifty-15m-data.csv",
            "1h": self.data_dir / "bank-nifty-1h-data.csv",
            "1d": self.data_dir / "bank-nifty-1d-data.csv",
        }

    def _read_csv(self, timeframe: str) -> pd.DataFrame:
        path = self.paths[timeframe]
        dataframe = pd.read_csv(path)
        dataframe.columns = [str(column).strip().lower() for column in dataframe.columns]
        dataframe["timestamp"] = pd.to_datetime(
            dataframe["date"] + " " + dataframe["time"],
            format="%d-%m-%Y %H:%M:%S",
            errors="coerce",
        ).dt.tz_localize(IST)
        dataframe = dataframe.dropna(subset=["timestamp", "open", "high", "low", "close"]).copy()
        for column in ["open", "high", "low", "close"]:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
        dataframe = dataframe.dropna(subset=["open", "high", "low", "close"]).copy()
        dataframe["volume"] = 0.0
        dataframe = dataframe.sort_values("timestamp").reset_index(drop=True)
        return dataframe[["timestamp", "open", "high", "low", "close", "volume"]]

    async def _read_all(self) -> dict[str, pd.DataFrame]:
        keys = ["15m", "1h", "1d"]
        frames = await asyncio.gather(*[asyncio.to_thread(self._read_csv, key) for key in keys])
        return dict(zip(keys, frames, strict=True))

    async def available_dates(self) -> list[str]:
        frames = await self._read_all()
        frame = frames["15m"]
        dates = sorted(frame["timestamp"].dt.date.unique())
        return [d.isoformat() for d in dates]

    def _to_candles(self, frame: pd.DataFrame) -> list[Candle]:
        if frame.empty:
            return []
        result = []
        for row in frame.itertuples(index=False):
            result.append(
                Candle(
                    time=int(row.timestamp.timestamp()),
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    volume=float(row.volume),
                )
            )
        return result

    async def stream_day(self, day: date) -> AsyncIterator[dict[str, list[Candle] | Candle]]:
        frames = await self._read_all()

        start = pd.Timestamp(datetime.combine(day, time(9, 15)), tz=IST)
        end = pd.Timestamp(datetime.combine(day, time(15, 30)), tz=IST)

        day_15m = frames["15m"][(frames["15m"]["timestamp"] >= start) & (frames["15m"]["timestamp"] <= end)]
        day_15m = day_15m.reset_index(drop=True)

        for row in day_15m.itertuples(index=False):
            now = row.timestamp
            slice_15m = frames["15m"][frames["15m"]["timestamp"] <= now].tail(120)
            slice_1h = frames["1h"][frames["1h"]["timestamp"] <= now].tail(120)
            slice_1d = frames["1d"][frames["1d"]["timestamp"] <= now].tail(120)
            current = self._to_candles(pd.DataFrame([row._asdict()]))[0]
            yield {
                "current": current,
                "window_15m": self._to_candles(slice_15m),
                "window_1h": self._to_candles(slice_1h),
                "window_1d": self._to_candles(slice_1d),
            }


class BacktestBrain:
    def __init__(self, portfolio: PortfolioManager) -> None:
        self.portfolio = portfolio
        self.active_trade: BacktestTrade | None = None
        self.last_event: dict | None = None

    def _direction(self, signal_type: str) -> Literal["BUY_CALL", "BUY_PUT"] | None:
        if signal_type == "BUY_CALL":
            return "BUY_CALL"
        if signal_type == "BUY_PUT":
            return "BUY_PUT"
        return None

    def _entry_option_price(self, spot: float) -> float:
        return max(20.0, spot * 0.005)

    def on_step(self, candle: Candle, analysis: AnalysisResponse) -> dict | None:
        self.last_event = None

        if self.active_trade:
            hit_stop = candle.low <= self.active_trade.spot_stop_loss if self.active_trade.direction == "BUY_CALL" else candle.high >= self.active_trade.spot_stop_loss
            hit_target = candle.high >= self.active_trade.spot_target if self.active_trade.direction == "BUY_CALL" else candle.low <= self.active_trade.spot_target

            if hit_stop:
                self.last_event = {
                    "type": "exit",
                    "trade": self.portfolio.settle_trade(self.active_trade, self.active_trade.spot_stop_loss, candle.time, "stop_loss"),
                }
                self.active_trade = None
                return self.last_event
            if hit_target:
                self.last_event = {
                    "type": "exit",
                    "trade": self.portfolio.settle_trade(self.active_trade, self.active_trade.spot_target, candle.time, "target"),
                }
                self.active_trade = None
                return self.last_event

            candle_time = datetime.fromtimestamp(candle.time, tz=IST_ZONE).time()
            if candle_time >= time(15, 15):
                self.last_event = {
                    "type": "exit",
                    "trade": self.portfolio.settle_trade(self.active_trade, candle.close, candle.time, "auto_square_off_1515"),
                }
                self.active_trade = None
                return self.last_event

        if not self.active_trade and analysis.signal.type != "NONE":
            direction = self._direction(analysis.signal.type)
            confirmation = analysis.forecast_confirmation
            if direction and confirmation and confirmation.agrees:
                self.active_trade = BacktestTrade(
                    direction=direction,
                    entry_spot=candle.close,
                    entry_option_price=self._entry_option_price(candle.close),
                    spot_stop_loss=analysis.signal.stopLoss,
                    spot_target=analysis.signal.target,
                    entry_time=candle.time,
                )
                self.last_event = {
                    "type": "entry",
                    "trade": {
                        "direction": direction,
                        "entry_spot": round(candle.close, 2),
                        "entry_time": candle.time,
                        "stop_loss": round(analysis.signal.stopLoss, 2),
                        "target": round(analysis.signal.target, 2),
                    },
                }
                return self.last_event

        return None

    def active_trade_snapshot(self) -> dict | None:
        if not self.active_trade:
            return None
        return {
            "direction": self.active_trade.direction,
            "entry_spot": round(self.active_trade.entry_spot, 2),
            "entry_time": self.active_trade.entry_time,
            "stop_loss": round(self.active_trade.spot_stop_loss, 2),
            "target": round(self.active_trade.spot_target, 2),
            "quantity": self.active_trade.quantity,
        }


class BacktestEngine:
    def __init__(self) -> None:
        self.loader = MultiTimeframeBacktestLoader()
        self.pipeline = AnalysisPipeline()
        self.forecast_service = ForecastService()

    async def run_day(self, day: date, speed: float = 1.0) -> AsyncIterator[dict]:
        portfolio = PortfolioManager()
        brain = BacktestBrain(portfolio)

        async for step in self.loader.stream_day(day):
            candle: Candle = step["current"]
            window_15m = step["window_15m"]
            window_1h = step["window_1h"]
            window_1d = step["window_1d"]

            analysis = await self.pipeline.analyze_from_backtest_windows(
                candles_15m=window_15m,
                candles_1h=window_1h,
                candles_1d=window_1d,
            )

            forecast: ForecastResult | None = None
            if analysis.signal.type != "NONE":
                forecast = await self.forecast_service.forecast(window_15m, horizon=6)
                analysis.forecast = forecast
                if forecast:
                    analysis.forecast_confirmation = self.pipeline.forecast_confirmer.confirm(
                        analysis.signal.type,
                        forecast,
                        analysis.indicators.get("atr", [1.0])[-1],
                    )

            event = brain.on_step(candle, analysis)
            sleep_seconds = max(0.05, 1 / max(speed, 0.1))

            yield {
                "real_candle": candle.model_dump(),
                "portfolio_state": portfolio.snapshot(),
                "active_trade": brain.active_trade_snapshot(),
                "jack_signals": {
                    "signal": analysis.signal.model_dump(),
                    "regime": analysis.regime.model_dump(),
                    "score": analysis.score.value,
                },
                "jill_forecast": forecast.p50[:6] if forecast else [],
                "event": event,
                "sleep_seconds": sleep_seconds,
            }
