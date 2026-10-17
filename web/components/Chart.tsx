"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  createChart,
  type UTCTimestamp,
} from "lightweight-charts";
import { ema, rsi } from "@/lib/indicators";
import type { Candle } from "@/lib/types";

const toTime = (iso: string) => (Date.parse(iso) / 1000) as UTCTimestamp;

function line(times: UTCTimestamp[], values: (number | null)[]) {
  return values.flatMap((v, i) => (v === null ? [] : [{ time: times[i], value: v }]));
}

type Levels = { entry: number; stop: number; target: number } | null;

export function Chart({ candles, levels = null }: { candles: Candle[]; levels?: Levels }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: dark ? "#8a97a8" : "#5b6676",
        // Verplichte TradingView-attributie (Apache-2.0 NOTICE)
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: dark ? "#161e28" : "#eef1f5" },
        horzLines: { color: dark ? "#161e28" : "#eef1f5" },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      localization: { locale: "nl-NL" },
    });

    const times = candles.map((c) => toTime(c.open_time));
    const closes = candles.map((c) => c.close);

    const price = chart.addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#f05252",
        wickUpColor: "#22c55e",
        wickDownColor: "#f05252",
        borderVisible: false,
      });
    price.setData(candles.map((c, i) => ({ time: times[i], open: c.open, high: c.high, low: c.low, close: c.close })));

    // Signaalniveaus van de actieve koopkans
    if (levels) {
      price.createPriceLine({ price: levels.target, color: "#22c55e", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "doel" });
      price.createPriceLine({ price: levels.entry, color: "#4f8cff", lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "instap" });
      price.createPriceLine({ price: levels.stop, color: "#f05252", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "stop" });
    }

    chart.addSeries(LineSeries, { color: "#4f8cff", lineWidth: 1, title: "EMA 50" }).setData(line(times, ema(closes, 50)));
    chart.addSeries(LineSeries, { color: "#a78bfa", lineWidth: 1, title: "EMA 200" }).setData(line(times, ema(closes, 200)));

    const volume = chart.addSeries(HistogramSeries, { priceScaleId: "volume", priceFormat: { type: "volume" } });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volume.setData(
      candles.map((c, i) => ({
        time: times[i],
        value: c.volume,
        color: c.close >= c.open ? "rgba(22,163,74,0.35)" : "rgba(220,38,38,0.35)",
      })),
    );

    // RSI in eigen paneel
    const rsiSeries = chart.addSeries(LineSeries, { color: "#f5a524", lineWidth: 1, title: "RSI 14" }, 1);
    rsiSeries.setData(line(times, rsi(closes, 14)));
    rsiSeries.createPriceLine({ price: 70, color: "#a3a3a3", lineStyle: 2, axisLabelVisible: false, lineWidth: 1, title: "" });
    rsiSeries.createPriceLine({ price: 30, color: "#a3a3a3", lineStyle: 2, axisLabelVisible: false, lineWidth: 1, title: "" });
    chart.panes()[1]?.setHeight(120);

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candles, levels]);

  return <div ref={ref} className="h-[560px] w-full" />;
}
