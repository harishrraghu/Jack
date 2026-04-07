"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  LineStyle,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { getBacktestDates } from "@/lib/api";
import type { BacktestPayload, Candle } from "@/lib/types";

type Speed = 1 | 2 | 4;

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

export function BacktestDashboard() {
  const [dates, setDates] = useState<string[]>([]);
  const [date, setDate] = useState<string>("");
  const [speed, setSpeed] = useState<Speed>(1);
  const [running, setRunning] = useState(false);
  const [portfolio, setPortfolio] = useState({ capital: 10000, day_pnl: 0 });
  const [activeTrade, setActiveTrade] = useState<BacktestPayload["active_trade"]>(null);
  const [signal, setSignal] = useState<BacktestPayload["jack_signals"]["signal"] | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ghostSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const candlesRef = useRef<CandlestickData<UTCTimestamp>[]>([]);
  const markersRef = useRef<
    Array<{
      time: UTCTimestamp;
      position: "aboveBar" | "belowBar";
      color: string;
      shape: "arrowUp" | "arrowDown";
      text: string;
    }>
  >([]);

  useEffect(() => {
    getBacktestDates().then((result) => {
      setDates(result);
      if (result[0]) setDate(result[0]);
    });
  }, []);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/backtest`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data) as BacktestPayload | { action: string };
      if ("action" in payload) {
        if (payload.action === "completed" || payload.action === "stopped") setRunning(false);
        return;
      }

      setPortfolio({
        capital: payload.portfolio_state.capital,
        day_pnl: payload.portfolio_state.day_pnl,
      });
      setActiveTrade(payload.active_trade);
      setSignal(payload.jack_signals.signal);

      const candle = payload.real_candle;
      const candleData: CandlestickData<UTCTimestamp> = {
        time: candle.time as UTCTimestamp,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      };
      candlesRef.current = [...candlesRef.current, candleData];
      mainSeriesRef.current?.setData(candlesRef.current);

      const forecastPoints = payload.jill_forecast.map((value, index) => ({
        time: (candle.time + (index + 1) * 900) as UTCTimestamp,
        value,
      }));
      ghostSeriesRef.current?.setData(forecastPoints);

      if (payload.event?.type === "entry") {
        markersRef.current.push({
          time: candle.time as UTCTimestamp,
          position: "belowBar",
          color: "#22c55e",
          shape: "arrowUp",
          text: "BUY",
        });
        mainSeriesRef.current?.setMarkers(markersRef.current);
      }
      if (payload.event?.type === "exit") {
        markersRef.current.push({
          time: candle.time as UTCTimestamp,
          position: "aboveBar",
          color: "#ef4444",
          shape: "arrowDown",
          text: "SELL",
        });
        mainSeriesRef.current?.setMarkers(markersRef.current);
      }
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    const container = document.getElementById("backtest-chart");
    if (!container) return;

    const chart = createChart(container, {
      autoSize: true,
      height: 520,
      layout: {
        background: { type: ColorType.Solid, color: "#0b1220" },
        textColor: "#d1d5db",
      },
      grid: {
        vertLines: { color: "rgba(148,163,184,0.15)" },
        horzLines: { color: "rgba(148,163,184,0.15)" },
      },
      rightPriceScale: { borderColor: "rgba(148,163,184,0.25)" },
      timeScale: { borderColor: "rgba(148,163,184,0.25)", timeVisible: true },
    });

    mainSeriesRef.current = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      borderVisible: false,
    });

    ghostSeriesRef.current = chart.addLineSeries({
      color: "rgba(96,165,250,0.35)",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
    });
    chartRef.current = chart;

    return () => chart.remove();
  }, []);

  const pnlColor = useMemo(() => (portfolio.day_pnl >= 0 ? "text-emerald-400" : "text-red-400"), [portfolio.day_pnl]);

  const send = (payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify(payload));
  };

  const start = () => {
    candlesRef.current = [];
    markersRef.current = [];
    mainSeriesRef.current?.setData([]);
    mainSeriesRef.current?.setMarkers([]);
    ghostSeriesRef.current?.setData([]);
    send({ action: "start", date, speed });
    setRunning(true);
  };

  return (
    <main className="min-h-screen bg-slate-950 p-4 text-slate-100 md:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-4">
        <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/80 p-4">
          <h1 className="text-xl font-semibold">Step-Forward Intraday Backtester</h1>
          <div className={`text-lg font-semibold ${pnlColor}`}>
            Capital: ₹{portfolio.capital.toFixed(2)} | Day PnL: {portfolio.day_pnl >= 0 ? "+" : ""}₹{portfolio.day_pnl.toFixed(2)}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <select value={date} onChange={(e) => setDate(e.target.value)} className="rounded bg-slate-800 px-3 py-2">
            {dates.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <button onClick={start} className="rounded bg-emerald-600 px-4 py-2">Play</button>
          <button onClick={() => send({ action: "pause" })} className="rounded bg-amber-600 px-4 py-2">Pause</button>
          <button onClick={() => send({ action: "step", date })} className="rounded bg-sky-600 px-4 py-2">Step</button>
          {[1, 2, 4].map((x) => (
            <button key={x} onClick={() => setSpeed(x as Speed)} className={`rounded px-3 py-2 ${speed === x ? "bg-indigo-600" : "bg-slate-700"}`}>
              {x}x
            </button>
          ))}
          <span className="text-sm text-slate-400">{running ? "Running" : "Paused"}</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div id="backtest-chart" className="h-[520px] rounded-xl border border-slate-800 bg-slate-900" />
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 text-lg font-medium">Jack Analysis</h2>
            {signal ? (
              <div className="space-y-2 text-sm">
                <p>Direction: <span className="font-semibold">{signal.type}</span></p>
                <p>Entry: {signal.entry.toFixed(2)}</p>
                <p>SL: {signal.stopLoss.toFixed(2)}</p>
                <p>TP: {signal.target.toFixed(2)}</p>
                <p>Confidence: {signal.confidence.toFixed(1)}</p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Waiting for signal...</p>
            )}
            {activeTrade && (
              <div className="mt-4 rounded border border-slate-700 p-3 text-sm">
                <p className="font-semibold">Active Trade</p>
                <p>{activeTrade.direction} @ {activeTrade.entry_spot}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
