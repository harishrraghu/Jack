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
    type: Literal[
        "trend_up", "trend_down", "range", "volatile",
        "squeeze", "weak_trend_up", "weak_trend_down"
    ]
    tradable: bool
    strength: float = 50.0
    ema_alignment: Literal["fully_bullish", "fully_bearish", "partial", "mixed"] = "mixed"
    bb_width_percentile: float = 50.0


class TrendHealth(BaseModel):
    status: Literal["healthy", "overextended", "weakening", "exhausted"]
    momentum: Literal["accelerating", "steady", "decelerating", "reversing"]
    rsi_context: str
    macd_histogram_slope: Literal["rising", "flat", "falling"]
    stoch_rsi_signal: Literal["bullish_cross", "bearish_cross", "neutral"]
    vwap_supporting: bool


class PriceLevel(BaseModel):
    price: float
    type: Literal["support", "resistance"]
    source: str
    strength: Literal["weak", "moderate", "strong"]


class ConfluenceZone(BaseModel):
    top: float
    bottom: float
    type: Literal["support", "resistance"]
    sources: list[str]
    strength: int


class StructureLevels(BaseModel):
    levels: list[PriceLevel]
    confluence_zones: list[ConfluenceZone]
    nearest_support: float
    nearest_resistance: float
    price_position: str
    supertrend_value: float
    supertrend_direction: Literal["up", "down"]
    in_squeeze: bool
    squeeze_fired: bool
    fib_levels: dict[str, float]


class VolumeAnalysis(BaseModel):
    candle_vs_avg: Literal["spike", "elevated", "normal", "dry"]
    volume_ratio: float
    obv_trend: Literal["rising", "flat", "falling"]
    obv_divergence: bool
    vwap_position: Literal["above", "below"]
    vwap_distance_atr: float
    price_volume_divergence: Literal["bullish_divergence", "bearish_divergence", "none"]
    volume_trend: Literal["expanding", "contracting", "flat"]
    volume_supports_move: bool


class StrategyPrerequisites(BaseModel):
    required_regime: list[str]
    layer2_health: list[str] | None = None
    layer4_volume: str | None = None
    additional: list[str] = []


class Strategy(BaseModel):
    name: str
    category: Literal["trend", "range", "squeeze", "volatile", "cross_regime"]
    matched: bool
    prerequisites_met: bool
    reasons: list[str]
    entry_price: float | None = None
    stop_loss: float | None = None
    target_price: float | None = None
    risk_reward: float | None = None


class ExitPlan(BaseModel):
    stop_loss: float
    stop_method: str
    target: float
    target_method: str
    risk_reward_ratio: float
    trailing_stop_method: str | None = None
    break_even_trigger: float | None = None


class ForecastResult(BaseModel):
    direction: Literal["up", "down"]
    magnitude: float
    p10: list[float]
    p50: list[float]
    p90: list[float]
    horizon: int
    confidence_band: float


class ForecastConfirmation(BaseModel):
    available: bool
    agrees: bool
    confident: bool
    no_reversal: bool
    confirmed: bool
    band_width: float | None = None
    forecast_direction: str | None = None


class Liquidity(BaseModel):
    event: Literal["sweep", "fvg"] | None
    direction: Literal["bullish", "bearish"] | None
    level: float | None


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
    structure: Structure | None = None
    regime: Regime
    liquidity: Liquidity
    score: Score
    signal: Signal
    narrative: Narrative
    drawings: list[Drawing]
    indicators: dict[str, list[float]]
    volume_analysis: VolumeAnalysis | None = None
    trend_health: TrendHealth | None = None
    structure_levels: StructureLevels | None = None
    forecast: ForecastResult | None = None
    forecast_confirmation: ForecastConfirmation | None = None
    exit_plan: ExitPlan | None = None
    strategies: list[Strategy] | None = None
