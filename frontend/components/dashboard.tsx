"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, BookOpen, ShieldAlert } from "lucide-react";
import { getAnalysis, getFeedback, getJournal } from "@/lib/api";
import type { AnalysisResponse, FeedbackMetrics, JournalEntry } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ChartPanel } from "@/components/chart-panel";

const timeframes = ["1d", "15m", "5m"] as const;

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
          getFeedback()
        ]);

        if (!active) {
          return;
        }

        setAnalysis(analysisResult);
        setJournal(journalResult);
        setFeedback(feedbackResult);
        setError(null);
      } catch (loadError) {
        if (!active) {
          return;
        }

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
    if (!analysis) {
      return "muted" as const;
    }
    if (analysis.signal.type === "BUY_CALL") {
      return "success" as const;
    }
    if (analysis.signal.type === "BUY_PUT") {
      return "danger" as const;
    }
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

  return (
    <main className="app-shell min-h-screen p-4 md:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-4">
        <div className="flex flex-col justify-between gap-4 rounded-[32px] border border-border/70 bg-white/70 p-6 backdrop-blur md:flex-row md:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-stone-500">
              BANKNIFTY Decision Support Engine
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              Multi-timeframe deterministic charting and narrative analyst
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
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  Current Regime
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Badge>{analysis.regime.type.replace("_", " ")}</Badge>
                <p>Bias: {analysis.context.bias}</p>
                <p>Day type: {analysis.context.dayType}</p>
                <p>Volatility: {analysis.context.volatility}</p>
                <p>Tradable: {analysis.regime.tradable ? "Yes" : "No"}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4" />
                  Active Signal
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Badge variant={signalVariant}>{analysis.signal.type}</Badge>
                <p>Entry: {analysis.signal.entry.toFixed(2)}</p>
                <p>Stop: {analysis.signal.stopLoss.toFixed(2)}</p>
                <p>Target: {analysis.signal.target.toFixed(2)}</p>
                <p>Confidence: {analysis.signal.confidence.toFixed(1)}</p>
                <p>Score: {analysis.score.value.toFixed(1)}</p>
                <Separator />
                <div className="space-y-2 text-stone-600">
                  {analysis.signal.reasons.map((reason) => (
                    <p key={reason}>{reason}</p>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldAlert className="h-4 w-4" />
                  Risk + Narrative
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{analysis.narrative.summary}</p>
                <p className="text-stone-600">{analysis.narrative.setup}</p>
                <p className="text-stone-600">{analysis.narrative.risk}</p>
                <p className="font-medium">{analysis.narrative.action}</p>
              </CardContent>
            </Card>

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
