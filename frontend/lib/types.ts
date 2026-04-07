export type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type DayContext = {
  bias: "bullish" | "bearish" | "neutral";
  dayType: "trend" | "range" | "event";
  volatility: "low" | "medium" | "high";
  keyLevels: number[];
};

export type Structure = {
  trend: "bullish" | "bearish" | "neutral";
  phase: "impulse" | "pullback";
};

export type Regime = {
  type:
    | "trend_up"
    | "trend_down"
    | "range"
    | "volatile"
    | "squeeze"
    | "weak_trend_up"
    | "weak_trend_down";
  tradable: boolean;
  strength: number;
  ema_alignment: "fully_bullish" | "fully_bearish" | "partial" | "mixed";
  bb_width_percentile: number;
};

export type TrendHealth = {
  status: "healthy" | "overextended" | "weakening" | "exhausted";
  momentum: "accelerating" | "steady" | "decelerating" | "reversing";
  rsi_context: string;
  macd_histogram_slope: "rising" | "flat" | "falling";
  stoch_rsi_signal: "bullish_cross" | "bearish_cross" | "neutral";
  vwap_supporting: boolean;
};

export type PriceLevel = {
  price: number;
  type: "support" | "resistance";
  source: string;
  strength: "weak" | "moderate" | "strong";
};

export type ConfluenceZone = {
  top: number;
  bottom: number;
  type: "support" | "resistance";
  sources: string[];
  strength: number;
};

export type StructureLevels = {
  levels: PriceLevel[];
  confluence_zones: ConfluenceZone[];
  nearest_support: number;
  nearest_resistance: number;
  price_position: string;
  supertrend_value: number;
  supertrend_direction: "up" | "down";
  in_squeeze: boolean;
  squeeze_fired: boolean;
  fib_levels: Record<string, number>;
};

export type VolumeAnalysis = {
  candle_vs_avg: "spike" | "elevated" | "normal" | "dry";
  volume_ratio: number;
  obv_trend: "rising" | "flat" | "falling";
  obv_divergence: boolean;
  vwap_position: "above" | "below";
  vwap_distance_atr: number;
  price_volume_divergence: "bullish_divergence" | "bearish_divergence" | "none";
  volume_trend: "expanding" | "contracting" | "flat";
  volume_supports_move: boolean;
};

export type Strategy = {
  name: string;
  category: "trend" | "range" | "squeeze" | "volatile" | "cross_regime";
  matched: boolean;
  prerequisites_met: boolean;
  reasons: string[];
  entry_price: number | null;
  stop_loss: number | null;
  target_price: number | null;
  risk_reward: number | null;
};

export type ExitPlan = {
  stop_loss: number;
  stop_method: string;
  target: number;
  target_method: string;
  risk_reward_ratio: number;
  trailing_stop_method: string | null;
  break_even_trigger: number | null;
};

export type ForecastResult = {
  direction: "up" | "down";
  magnitude: number;
  p10: number[];
  p50: number[];
  p90: number[];
  horizon: number;
  confidence_band: number;
};

export type ForecastConfirmation = {
  available: boolean;
  agrees: boolean;
  confident: boolean;
  no_reversal: boolean;
  confirmed: boolean;
  band_width: number | null;
  forecast_direction: string | null;
};

export type Liquidity = {
  event: "sweep" | "fvg" | null;
  direction: "bullish" | "bearish" | null;
  level: number | null;
};

export type Score = {
  value: number;
};

export type Signal = {
  type: "BUY_CALL" | "BUY_PUT" | "NONE";
  entry: number;
  stopLoss: number;
  target: number;
  confidence: number;
  reasons: string[];
};

export type Drawing =
  | { type: "line"; data: { id: string; label: string; price: number; color: string } }
  | { type: "zone"; data: { id: string; label: string; top: number; bottom: number; color: string } }
  | { type: "label"; data: { id: string; label: string; price: number; color: string } };

export type Narrative = {
  regime: string;
  summary: string;
  setup: string;
  risk: string;
  action: string;
};

export type JournalEntry = {
  id: number;
  timestamp: string;
  signal: Signal;
  outcome: "win" | "loss" | "neutral";
  notes: string[];
  strategyName: string;
};

export type AnalysisResponse = {
  symbol: string;
  timeframe: string;
  candles: Candle[];
  context: DayContext;
  structure?: Structure | null;
  regime: Regime;
  liquidity: Liquidity;
  score: Score;
  signal: Signal;
  narrative: Narrative;
  drawings: Drawing[];
  indicators: Record<string, number[]>;
  volume_analysis?: VolumeAnalysis | null;
  trend_health?: TrendHealth | null;
  structure_levels?: StructureLevels | null;
  forecast?: ForecastResult | null;
  forecast_confirmation?: ForecastConfirmation | null;
  exit_plan?: ExitPlan | null;
  strategies?: Strategy[] | null;
};

export type FeedbackMetrics = {
  overallWinRate: number;
  strategyBreakdown: Array<{ strategy: string; winRate: number; samples: number }>;
  regimeBreakdown: Array<{ regime: string; winRate: number; samples: number }>;
};

export type BacktestPayload = {
  real_candle: Candle;
  portfolio_state: {
    starting_capital: number;
    capital: number;
    day_pnl: number;
    realized_pnl: number;
    total_fees: number;
    trades_count: number;
  };
  active_trade: {
    direction: "BUY_CALL" | "BUY_PUT";
    entry_spot: number;
    entry_time: number;
    stop_loss: number;
    target: number;
    quantity: number;
  } | null;
  jack_signals: {
    signal: Signal;
    regime: Regime;
    score: number;
  };
  jill_forecast: number[];
  event: {
    type: "entry" | "exit";
    trade: Record<string, unknown>;
  } | null;
};
