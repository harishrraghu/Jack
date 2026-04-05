from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class DayContext(BaseModel):
    bias: Literal["bullish", "bearish", "neutral"]
    dayType: Literal["trend", "range", "event"]
    volatility: Literal["low", "medium", "high"]
    keyLevels: list[float]


class Structure(BaseModel):
    trend: Literal["bullish", "bearish", "neutral"]
    phase: Literal["impulse", "pullback"]


class Regime(BaseModel):
    type: Literal["trend_up", "trend_down", "range"]
    tradable: bool


class Liquidity(BaseModel):
    event: Literal["sweep", "fvg"] | None
    direction: Literal["bullish", "bearish"] | None
    level: float | None


class Strategy(BaseModel):
    name: str
    matched: bool
    reasons: list[str]


class Score(BaseModel):
    value: float


class Signal(BaseModel):
    type: Literal["BUY_CALL", "BUY_PUT", "NONE"]
    entry: float
    stopLoss: float
    target: float
    confidence: float
    reasons: list[str]


class Drawing(BaseModel):
    type: Literal["line", "zone", "label"]
    data: dict[str, Any]


class Narrative(BaseModel):
    regime: str
    summary: str
    setup: str
    risk: str
    action: str


class JournalEntry(BaseModel):
    id: int | None = None
    timestamp: datetime
    signal: Signal
    outcome: Literal["win", "loss", "neutral"]
    notes: list[str]
    strategyName: str


class FeedbackMetric(BaseModel):
    strategy: str
    winRate: float
    samples: int


class RegimeFeedbackMetric(BaseModel):
    regime: str
    winRate: float
    samples: int


class FeedbackMetrics(BaseModel):
    overallWinRate: float
    strategyBreakdown: list[FeedbackMetric]
    regimeBreakdown: list[RegimeFeedbackMetric]


class AnalysisResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: list[Candle]
    context: DayContext
    structure: Structure
    regime: Regime
    liquidity: Liquidity
    score: Score
    signal: Signal
    narrative: Narrative
    drawings: list[Drawing]
    indicators: dict[str, list[float]]

