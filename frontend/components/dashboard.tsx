"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Layers,
  ShieldAlert,
  TrendingUp,
  Volume2,
  Zap,
} from "lucide-react";
import { getAnalysis, getFeedback, getJournal } from "@/lib/api";
import type { AnalysisResponse, FeedbackMetrics, JournalEntry } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ChartPanel } from "@/components/chart-panel";

const timeframes = ["1d", "15m", "5m"] as const;

function LayerDot({ status }: { status: "pass" | "caution" | "fail" | "skip" }) {
  const colors = {
    pass: "bg-green-500",
    caution: "bg-amber-400",
    fail: "bg-red-500",
    skip: "bg-stone-300",
  };
  return <span className={`inline-block h-2 w-2 rounded-full ${colors[status]}`} />;
}

export function Dashboard() {
  const [timeframe, setTimeframe] = useState<(typeof timeframes)[number]>("15m");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [feedback, setFeedback] = useState<FeedbackMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [analysisResult, journalResult, feedbackResult] = await Promise.all([
          getAnalysis(timeframe),
          getJournal(),
          getFeedback(),
        ]);

        if (!active) return;
        setAnalysis(analysisResult);
        setJournal(journalResult);
        setFeedback(feedbackResult);
        setError(null);
      } catch (loadError) {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard");
      }
    }

    load();
    const intervalId = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [timeframe]);

  const signalVariant = useMemo(() => {
    if (!analysis) return "muted" as const;
    if (analysis.signal.type === "BUY_CALL") return "success" as const;
    if (analysis.signal.type === "BUY_PUT") return "danger" as const;
    return "muted" as const;
  }, [analysis]);

  if (error) {
    return (
      <main className="app-shell min-h-screen p-6 md:p-8">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle>Dashboard Unavailable</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-stone-600">{error}</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!analysis || !feedback) {
    return (
      <main className="app-shell min-h-screen p-6 md:p-8">
        <div className="mx-auto flex max-w-7xl items-center justify-center py-40 text-sm text-stone-600">
          Loading deterministic BANKNIFTY analysis...
        </div>
      </main>
    );
  }

  const { regime, context, signal, score, narrative, trend_health, volume_analysis, structure_levels, forecast_confirmation, exit_plan, strategies } = analysis;

  const matchedStrategies = strategies?.filter((s) => s.matched && s.prerequisites_met) ?? [];

  return (
    <main className="app-shell min-h-screen p-4 md:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-4">
        {/* Header */}
        <div className="flex flex-col justify-between gap-4 rounded-[32px] border border-border/70 bg-white/70 p-6 backdrop-blur md:flex-row md:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-stone-500">
              BANKNIFTY Decision Support Engine
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              Jack + Jill — 7-Layer Deterministic + AI Analyst
            </h1>
          </div>
          <div className="flex flex-wrap gap-2">
            {timeframes.map((item) => (
              <button
                key={item}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  timeframe === item ? "bg-primary text-primary-foreground" : "bg-white text-foreground"
                }`}
                onClick={() => setTimeframe(item)}
              >
                {item.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,4fr)_minmax(320px,1fr)]">
          <Card className="p-4">
            <ChartPanel analysis={analysis} />
          </Card>

          <div className="grid gap-4">
            {/* Layer Status Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Layers className="h-4 w-4" />
                  Layer Status (Jack)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {/* Layer 1 */}
                <div className="flex items-center gap-2">
                  <LayerDot status={regime.tradable ? "pass" : "caution"} />
                  <span className="font-medium">L1 Regime:</span>
                  <span className="text-stone-600">{regime.type.replace(/_/g, " ")} ({regime.strength.toFixed(0)}%)</span>
                </div>
                {/* Layer 2 */}
                <div className="flex items-center gap-2">
                  <LayerDot
                    status={
                      !trend_health
                        ? "skip"
                        : trend_health.status === "healthy"
                        ? "pass"
                        : trend_health.status === "exhausted"
                        ? "fail"
                        : "caution"
                    }
                  />
                  <span className="font-medium">L2 Health:</span>
                  <span className="text-stone-600">
                    {trend_health ? `${trend_health.status}, ${trend_health.momentum}` : "skipped (non-trending)"}
                  </span>
                </div>
                {/* Layer 3 */}
                <div className="flex items-center gap-2">
                  <LayerDot status={structure_levels ? "pass" : "fail"} />
                  <span className="font-medium">L3 Structure:</span>
                  <span className="text-stone-600 truncate max-w-[160px]">
                    {structure_levels
                      ? `S: ${structure_levels.nearest_support.toFixed(0)} / R: ${structure_levels.nearest_resistance.toFixed(0)}`
                      : "unavailable"}
                  </span>
                </div>
                {/* Layer 4 */}
                <div className="flex items-center gap-2">
                  <LayerDot
                    status={
                      !volume_analysis
                        ? "skip"
                        : volume_analysis.volume_supports_move
                        ? "pass"
                        : volume_analysis.obv_divergence
                        ? "fail"
                        : "caution"
                    }
                  />
                  <span className="font-medium">L4 Volume:</span>
                  <span className="text-stone-600">
                    {volume_analysis
                      ? `${volume_analysis.candle_vs_avg} (${volume_analysis.volume_ratio.toFixed(1)}x)`
                      : "unavailable"}
                  </span>
                </div>
                {/* Layer 5 */}
                <div className="flex items-center gap-2">
                  <LayerDot status={matchedStrategies.length > 0 ? "pass" : "caution"} />
                  <span className="font-medium">L5 Strategies:</span>
                  <span className="text-stone-600">
                    {matchedStrategies.length > 0
                      ? matchedStrategies.map((s) => s.name.split(" ").slice(0, 2).join(" ")).join(", ")
                      : "none matched"}
                  </span>
                </div>
                {/* Layer 6 */}
                <div className="flex items-center gap-2">
                  <LayerDot
                    status={
                      !exit_plan
                        ? "skip"
                        : exit_plan.risk_reward_ratio >= 2
                        ? "pass"
                        : exit_plan.risk_reward_ratio >= 1.5
                        ? "caution"
                        : "fail"
                    }
                  />
                  <span className="font-medium">L6 Exit:</span>
                  <span className="text-stone-600">
                    {exit_plan ? `R:R ${exit_plan.risk_reward_ratio.toFixed(1)} via ${exit_plan.stop_method.split(" ").slice(0, 2).join(" ")}` : "no signal"}
                  </span>
                </div>
                {/* Layer 7 Jill */}
                <div className="flex items-center gap-2">
                  <LayerDot
                    status={
                      !forecast_confirmation || !forecast_confirmation.available
                        ? "skip"
                        : forecast_confirmation.confirmed
                        ? "pass"
                        : "caution"
                    }
                  />
                  <span className="font-medium">L7 Jill:</span>
                  <span className="text-stone-600">
                    {!forecast_confirmation || !forecast_confirmation.available
                      ? "TimesFM not loaded"
                      : forecast_confirmation.confirmed
                      ? "confirmed"
                      : `flags: ${[
                          !forecast_confirmation.agrees && "direction",
                          !forecast_confirmation.confident && "confidence",
                          !forecast_confirmation.no_reversal && "reversal",
                        ]
                          .filter(Boolean)
                          .join(", ")}`}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Current Regime */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  Current Regime
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Badge>{regime.type.replace(/_/g, " ")}</Badge>
                <p>Bias: {context.bias} | Day: {context.dayType} | Vol: {context.volatility}</p>
                <p>EMA alignment: {regime.ema_alignment.replace(/_/g, " ")}</p>
                <p>BB width percentile: {regime.bb_width_percentile.toFixed(0)}th</p>
                <p>Tradable: {regime.tradable ? "Yes" : "No"} | Strength: {regime.strength.toFixed(0)}/100</p>
              </CardContent>
            </Card>

            {/* Volume Card */}
            {volume_analysis && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Volume2 className="h-4 w-4" />
                    Volume Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span
                      className={
                        volume_analysis.candle_vs_avg === "spike"
                          ? "text-green-600 font-medium"
                          : volume_analysis.candle_vs_avg === "dry"
                          ? "text-red-500"
                          : "text-stone-700"
                      }
                    >
                      {volume_analysis.candle_vs_avg.toUpperCase()}
                    </span>
                    <span className="text-stone-500">({volume_analysis.volume_ratio.toFixed(1)}x avg)</span>
                  </div>
                  <p>
                    OBV: <span className={volume_analysis.obv_trend === "rising" ? "text-green-600" : volume_analysis.obv_trend === "falling" ? "text-red-500" : ""}>{volume_analysis.obv_trend}</span>
                    {volume_analysis.obv_divergence && (
                      <span className="ml-1 text-amber-600 font-medium">⚠ divergence</span>
                    )}
                  </p>
                  <p>
                    VWAP: price is{" "}
                    <span className={volume_analysis.vwap_position === "above" ? "text-green-600" : "text-red-500"}>
                      {volume_analysis.vwap_position}
                    </span>{" "}
                    ({volume_analysis.vwap_distance_atr.toFixed(1)}x ATR away)
                  </p>
                  {volume_analysis.price_volume_divergence !== "none" && (
                    <p className="text-amber-600 font-medium">
                      ⚠ {volume_analysis.price_volume_divergence.replace(/_/g, " ")}
                    </p>
                  )}
                  <p>
                    Volume trend:{" "}
                    <span className={volume_analysis.volume_trend === "expanding" ? "text-green-600" : volume_analysis.volume_trend === "contracting" ? "text-red-500" : ""}>
                      {volume_analysis.volume_trend}
                    </span>
                  </p>
                  <p className={volume_analysis.volume_supports_move ? "text-green-600 font-medium" : "text-red-500 font-medium"}>
                    {volume_analysis.volume_supports_move ? "✓ Volume supports move" : "✗ Volume does not support move"}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Structure Card */}
            {structure_levels && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <TrendingUp className="h-4 w-4" />
                    Structure & Levels
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <p className="text-stone-600 text-xs">{structure_levels.price_position}</p>
                  <p>
                    Support: <span className="text-green-600 font-medium">{structure_levels.nearest_support.toFixed(0)}</span>
                    {" | "}
                    Resistance: <span className="text-red-500 font-medium">{structure_levels.nearest_resistance.toFixed(0)}</span>
                  </p>
                  <p>
                    Supertrend:{" "}
                    <span className={structure_levels.supertrend_direction === "up" ? "text-green-600" : "text-red-500"}>
                      {structure_levels.supertrend_value.toFixed(0)} ({structure_levels.supertrend_direction})
                    </span>
                  </p>
                  {structure_levels.confluence_zones.length > 0 && (
                    <div>
                      <p className="font-medium">Confluence zones:</p>
                      {structure_levels.confluence_zones.slice(0, 2).map((z, i) => (
                        <p key={i} className="text-stone-600 text-xs">
                          {z.type} {z.bottom.toFixed(0)}–{z.top.toFixed(0)} ({z.sources.length} sources: {z.sources.slice(0, 3).join(", ")})
                        </p>
                      ))}
                    </div>
                  )}
                  {structure_levels.in_squeeze && (
                    <p className="text-amber-600 font-medium">⚡ Squeeze active</p>
                  )}
                  {structure_levels.squeeze_fired && (
                    <p className="text-green-600 font-medium">🔥 Squeeze just fired!</p>
                  )}
                  {Object.keys(structure_levels.fib_levels).length > 0 && (
                    <div className="text-xs text-stone-500">
                      Fib: {Object.entries(structure_levels.fib_levels).map(([k, v]) => `${k}=${v.toFixed(0)}`).join(" | ")}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Active Signal */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4" />
                  Active Signal
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Badge variant={signalVariant}>{signal.type}</Badge>
                <p>Entry: {signal.entry.toFixed(2)}</p>
                <p>Stop: {signal.stopLoss.toFixed(2)}</p>
                <p>Target: {signal.target.toFixed(2)}</p>
                {exit_plan && (
                  <p className="text-xs text-stone-500">
                    R:R {exit_plan.risk_reward_ratio.toFixed(1)} | Stop: {exit_plan.stop_method} | Target: {exit_plan.target_method}
                  </p>
                )}
                <p>Confidence: {signal.confidence.toFixed(1)} | Score: {score.value.toFixed(1)}</p>
                <Separator />
                <div className="space-y-1 text-stone-600 text-xs">
                  {signal.reasons.map((reason, i) => (
                    <p key={i}>{reason}</p>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Jill Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Zap className="h-4 w-4" />
                  Jill (TimesFM)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {!forecast_confirmation || !forecast_confirmation.available ? (
                  <p className="text-stone-400 italic">TimesFM not loaded — Jack operating solo</p>
                ) : (
                  <>
                    <p>
                      Forecast:{" "}
                      <span className={forecast_confirmation.forecast_direction === "up" ? "text-green-600 font-medium" : "text-red-500 font-medium"}>
                        {forecast_confirmation.forecast_direction}
                      </span>
                      {forecast_confirmation.band_width !== null && (
                        <span className="text-stone-500 ml-1">(band ±{forecast_confirmation.band_width.toFixed(0)})</span>
                      )}
                    </p>
                    <div className="space-y-1">
                      {[
                        { label: "Direction agrees", ok: forecast_confirmation.agrees },
                        { label: "Confidence tight", ok: forecast_confirmation.confident },
                        { label: "No reversal risk", ok: forecast_confirmation.no_reversal },
                      ].map(({ label, ok }) => (
                        <div key={label} className="flex items-center gap-2">
                          <span className={ok ? "text-green-500" : "text-red-500"}>{ok ? "✓" : "✗"}</span>
                          <span className={ok ? "" : "text-stone-400"}>{label}</span>
                        </div>
                      ))}
                    </div>
                    <p className={forecast_confirmation.confirmed ? "text-green-600 font-medium" : "text-amber-600 font-medium"}>
                      {forecast_confirmation.confirmed ? "✓ Jill confirms signal" : "⚠ Jill flags concerns"}
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Risk + Narrative */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldAlert className="h-4 w-4" />
                  Risk + Narrative
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{narrative.summary}</p>
                <p className="text-stone-600">{narrative.setup}</p>
                <p className="text-stone-600">{narrative.risk}</p>
                <p className="font-medium">{narrative.action}</p>
              </CardContent>
            </Card>

            {/* Live Journal */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BookOpen className="h-4 w-4" />
                  Live Journal
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="max-h-[260px] space-y-3">
                  <div className="space-y-3">
                    {journal.map((entry) => (
                      <div key={entry.id} className="rounded-2xl border border-border/70 bg-stone-50 p-3 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium">{entry.strategyName}</span>
                          <Badge
                            variant={
                              entry.outcome === "win" ? "success" : entry.outcome === "loss" ? "danger" : "warning"
                            }
                          >
                            {entry.outcome}
                          </Badge>
                        </div>
                        <p className="mt-2">{entry.signal.type}</p>
                        <p className="text-stone-500">{new Date(entry.timestamp).toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Feedback Loop */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Feedback Loop</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>Overall win rate: {feedback.overallWinRate.toFixed(1)}%</p>
                {feedback.strategyBreakdown.map((item) => (
                  <p key={item.strategy} className="text-stone-600">
                    {item.strategy}: {item.winRate.toFixed(1)}% ({item.samples} samples)
                  </p>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}
