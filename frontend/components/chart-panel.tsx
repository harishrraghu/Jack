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
  type UTCTimestamp,
} from "lightweight-charts";
import type { AnalysisResponse, Candle, Drawing } from "@/lib/types";

type Props = {
  analysis: AnalysisResponse;
};

function getBounds(candles: Candle[]) {
  return {
    high: Math.max(...candles.map((c) => c.high)),
    low: Math.min(...candles.map((c) => c.low)),
  };
}

function priceToY(price: number, min: number, max: number, height: number) {
  if (max === min) return height / 2;
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
          // Different opacity for different zone types
          const isConfluence = drawing.data.id.startsWith("confluence");
          const isBB = drawing.data.id === "bb-bands";
          const isVWAP = drawing.data.id.startsWith("vwap-band");
          const isForecast = drawing.data.id === "forecast-band";
          const fillOpacity = isConfluence ? "0.10" : isBB ? "0.06" : isVWAP ? "0.08" : isForecast ? "0.12" : "0.14";

          return (
            <g key={drawing.data.id}>
              <rect
                x="24"
                y={Math.min(top, bottom)}
                width="94%"
                height={Math.abs(bottom - top)}
                fill={drawing.data.color}
                fillOpacity={fillOpacity}
                stroke={drawing.data.color}
                strokeOpacity={isConfluence || isBB || isVWAP ? "0.3" : "0.6"}
                strokeDasharray={isBB || isVWAP ? "2 4" : "4 4"}
              />
              <text
                x="32"
                y={Math.min(top, bottom) + 14}
                fill={drawing.data.color}
                fontSize="10"
                opacity="0.7"
              >
                {drawing.data.label}
              </text>
            </g>
          );
        }

        // line or label
        const y = priceToY(drawing.data.price, bounds.low, bounds.high, 560);
        const isSupertrend = drawing.data.id === "supertrend";
        const isPivot = ["pivot", "pivot_r1", "pivot_r2", "pivot_s1", "pivot_s2"].includes(drawing.data.id);

        return (
          <g key={drawing.data.id}>
            <line
              x1="24"
              x2="100%"
              y1={y}
              y2={y}
              stroke={drawing.data.color}
              strokeWidth={isSupertrend ? "2" : "1.5"}
              strokeDasharray={
                drawing.type === "label"
                  ? isPivot
                    ? "6 4"
                    : "3 4"
                  : isSupertrend
                  ? "none"
                  : "8 5"
              }
              opacity={isPivot ? "0.6" : "1"}
            />
            <text
              x="28"
              y={Math.max(18, y - 5)}
              fill={drawing.data.color}
              fontSize={isPivot ? "10" : "12"}
              opacity={isPivot ? "0.7" : "1"}
            >
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
  const ema200Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const vwapRef = useRef<ISeriesApi<"Area"> | null>(null);
  const supertrendRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      height: 560,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#203537",
      },
      grid: {
        vertLines: { color: "rgba(32, 53, 55, 0.08)" },
        horzLines: { color: "rgba(32, 53, 55, 0.08)" },
      },
      rightPriceScale: { borderColor: "rgba(32, 53, 55, 0.18)" },
      timeScale: {
        borderColor: "rgba(32, 53, 55, 0.18)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleOptions: CandlestickSeriesPartialOptions = {
      upColor: "#2c7a64",
      downColor: "#b6423c",
      borderVisible: false,
      wickUpColor: "#2c7a64",
      wickDownColor: "#b6423c",
    };
    const ema21Options: LineSeriesPartialOptions = { color: "#1f7a8c", lineWidth: 2 };
    const ema50Options: LineSeriesPartialOptions = { color: "#f08a4b", lineWidth: 2 };
    const ema200Options: LineSeriesPartialOptions = {
      color: "#7c3aed",
      lineWidth: 1,
      lineStyle: 2, // dashed
    };
    const vwapOptions: AreaSeriesPartialOptions = {
      lineColor: "#5c4d7d",
      topColor: "rgba(92, 77, 125, 0.16)",
      bottomColor: "rgba(92, 77, 125, 0.02)",
    };
    const supertrendOptions: LineSeriesPartialOptions = {
      color: "#16a34a",
      lineWidth: 2,
    };

    candleSeriesRef.current = chart.addCandlestickSeries(candleOptions);
    ema21Ref.current = chart.addLineSeries(ema21Options);
    ema50Ref.current = chart.addLineSeries(ema50Options);
    ema200Ref.current = chart.addLineSeries(ema200Options);
    vwapRef.current = chart.addAreaSeries(vwapOptions);
    supertrendRef.current = chart.addLineSeries(supertrendOptions);
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
    const ema200 = ema200Ref.current;
    const vwap = vwapRef.current;
    const supertrend = supertrendRef.current;

    if (!candleSeries || !ema21 || !ema50 || !ema200 || !vwap || !supertrend) return;

    const times = analysis.candles.map((c) => c.time as UTCTimestamp);

    candleSeries.setData(
      analysis.candles.map((candle) => ({ ...candle, time: candle.time as UTCTimestamp }))
    );

    ema21.setData(
      analysis.indicators.ema21.map((value, i) => ({ time: times[i], value }))
    );
    ema50.setData(
      analysis.indicators.ema50.map((value, i) => ({ time: times[i], value }))
    );

    if (analysis.indicators.ema200) {
      ema200.setData(
        analysis.indicators.ema200.map((value, i) => ({ time: times[i], value }))
      );
    }

    vwap.setData(
      analysis.indicators.vwap.map((value, i) => ({ time: times[i], value }))
    );

    // Supertrend with direction-based color
    if (analysis.indicators.supertrend && analysis.indicators.supertrend_direction) {
      const stData = analysis.indicators.supertrend.map((value, i) => ({
        time: times[i],
        value,
      }));
      supertrend.setData(stData);

      // direction encoded as 1.0=up, 0.0=down
      const lastDir = analysis.indicators.supertrend_direction[analysis.indicators.supertrend_direction.length - 1];
      supertrend.applyOptions({
        color: lastDir >= 0.5 ? "#16a34a" : "#dc2626",
      });
    } else {
      supertrend.setData([]);
    }

    chartRef.current?.timeScale().fitContent();
  }, [analysis]);

  return (
    <div className="relative h-[560px] overflow-hidden rounded-[28px] border border-border/70 bg-white/60">
      <div ref={containerRef} className="h-full w-full" />
      <Overlay drawings={analysis.drawings} candles={analysis.candles} />
    </div>
  );
}
