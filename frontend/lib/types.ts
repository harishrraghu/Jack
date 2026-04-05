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
  type: "trend_up" | "trend_down" | "range";
  tradable: boolean;
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
  structure: Structure;
  regime: Regime;
  liquidity: Liquidity;
  score: Score;
  signal: Signal;
  narrative: Narrative;
  drawings: Drawing[];
  indicators: Record<string, number[]>;
};

export type FeedbackMetrics = {
  overallWinRate: number;
  strategyBreakdown: Array<{ strategy: string; winRate: number; samples: number }>;
  regimeBreakdown: Array<{ regime: string; winRate: number; samples: number }>;
};

