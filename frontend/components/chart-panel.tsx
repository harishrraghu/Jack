"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type AreaSeriesPartialOptions,
  type CandlestickSeriesPartialOptions,
  type LineSeriesPartialOptions,
  type UTCTimestamp
} from "lightweight-charts";
import type { AnalysisResponse, Candle, Drawing } from "@/lib/types";

type Props = {
  analysis: AnalysisResponse;
};

function getBounds(candles: Candle[]) {
  return {
    high: Math.max(...candles.map((c) => c.high)),
    low: Math.min(...candles.map((c) => c.low))
  };
}

function priceToY(price: number, min: number, max: number, height: number) {
  if (max === min) {
    return height / 2;
  }
  return ((max - price) / (max - min)) * height;
}

function Overlay({ drawings, candles }: { drawings: Drawing[]; candles: Candle[] }) {
  const bounds = useMemo(() => getBounds(candles), [candles]);

  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full">
      {drawings.map((drawing) => {
        if (drawing.type === "zone") {
          const top = priceToY(drawing.data.top, bounds.low, bounds.high, 560);
          const bottom = priceToY(drawing.data.bottom, bounds.low, bounds.high, 560);
          return (
            <g key={drawing.data.id}>
              <rect
                x="24"
                y={Math.min(top, bottom)}
                width="94%"
                height={Math.abs(bottom - top)}
                fill={drawing.data.color}
                fillOpacity="0.14"
                stroke={drawing.data.color}
                strokeDasharray="4 4"
              />
              <text x="32" y={Math.min(top, bottom) + 18} fill={drawing.data.color} fontSize="12">
                {drawing.data.label}
              </text>
            </g>
          );
        }

        const y = priceToY(drawing.data.price, bounds.low, bounds.high, 560);
        return (
          <g key={drawing.data.id}>
            <line
              x1="24"
              x2="100%"
              y1={y}
              y2={y}
              stroke={drawing.data.color}
              strokeWidth="1.5"
              strokeDasharray={drawing.type === "label" ? "3 4" : "8 5"}
            />
            <text x="28" y={Math.max(18, y - 6)} fill={drawing.data.color} fontSize="12">
              {drawing.data.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ChartPanel({ analysis }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ema21Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ema50Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const vwapRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const chart = createChart(containerRef.current, {
      autoSize: true,
      height: 560,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#203537"
      },
      grid: {
        vertLines: { color: "rgba(32, 53, 55, 0.08)" },
        horzLines: { color: "rgba(32, 53, 55, 0.08)" }
      },
      rightPriceScale: { borderColor: "rgba(32, 53, 55, 0.18)" },
      timeScale: {
        borderColor: "rgba(32, 53, 55, 0.18)",
        timeVisible: true,
        secondsVisible: false
      }
    });

    const candleOptions: CandlestickSeriesPartialOptions = {
      upColor: "#2c7a64",
      downColor: "#b6423c",
      borderVisible: false,
      wickUpColor: "#2c7a64",
      wickDownColor: "#b6423c"
    };
    const ema21Options: LineSeriesPartialOptions = { color: "#1f7a8c", lineWidth: 2 };
    const ema50Options: LineSeriesPartialOptions = { color: "#f08a4b", lineWidth: 2 };
    const vwapOptions: AreaSeriesPartialOptions = {
      lineColor: "#5c4d7d",
      topColor: "rgba(92, 77, 125, 0.16)",
      bottomColor: "rgba(92, 77, 125, 0.02)"
    };

    candleSeriesRef.current = chart.addCandlestickSeries(candleOptions);
    ema21Ref.current = chart.addLineSeries(ema21Options);
    ema50Ref.current = chart.addLineSeries(ema50Options);
    vwapRef.current = chart.addAreaSeries(vwapOptions);
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const ema21 = ema21Ref.current;
    const ema50 = ema50Ref.current;
    const vwap = vwapRef.current;
    if (!candleSeries || !ema21 || !ema50 || !vwap) {
      return;
    }

    candleSeries.setData(
      analysis.candles.map((candle) => ({ ...candle, time: candle.time as UTCTimestamp }))
    );
    ema21.setData(
      analysis.indicators.ema21.map((value, index) => ({
        time: analysis.candles[index]?.time as UTCTimestamp,
        value
      }))
    );
    ema50.setData(
      analysis.indicators.ema50.map((value, index) => ({
        time: analysis.candles[index]?.time as UTCTimestamp,
        value
      }))
    );
    vwap.setData(
      analysis.indicators.vwap.map((value, index) => ({
        time: analysis.candles[index]?.time as UTCTimestamp,
        value
      }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [analysis]);

  return (
    <div className="relative h-[560px] overflow-hidden rounded-[28px] border border-border/70 bg-white/60">
      <div ref={containerRef} className="h-full w-full" />
      <Overlay drawings={analysis.drawings} candles={analysis.candles} />
    </div>
  );
}
