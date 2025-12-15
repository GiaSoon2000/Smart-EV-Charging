"use client";

import { useState, useEffect, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { motion } from "framer-motion";
import { ChartTooltip } from "@/components/ui/chart-tooltip";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { ModeToggle } from "@/components/ui/mode-toggle";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type TimelinePoint = { rel_time: string; abs_time: string; soc: number };

type PredictResponse = {
  hours: number;
  final_battery: number;
  timeline: TimelinePoint[];
  start_time: string;
  end_time: string;
  cost_now: number;
  cost_optimized: number;
  savings: number;
  meets_departure: boolean;
  night_tariff_applied: boolean;
  info?: string;
};

export default function EVOptimizerPage() {
  const [battery, setBattery] = useState<number>(25);
  const [power, setPower] = useState<number>(7);
  const [targetSoc, setTargetSoc] = useState<number>(80);
  const [departure, setDeparture] = useState<string>("19:00");
  const [cheapMode, setCheapMode] = useState<boolean>(true);

  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<string>("—");
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

  /** -----------------------------
   * Resolve start/end absolute timestamps
   * ----------------------------- */
  const buildDateFromHHMM = (hhmm: string): Date | null => {
    const [h, m] = hhmm.split(":").map(Number);
    if (Number.isNaN(h) || Number.isNaN(m)) return null;

    const now = new Date();
    const d = new Date(now);
    d.setHours(h, m, 0, 0);

    // If the time has passed, treat it as tomorrow
    if (d.getTime() <= now.getTime()) {
      d.setDate(d.getDate() + 1);
    }
    return d;
  };

  const startDate = result ? buildDateFromHHMM(result.start_time) : null;
  const endDateRaw = result ? buildDateFromHHMM(result.end_time) : null;

  const endDate =
    startDate && endDateRaw && endDateRaw < startDate
      ? new Date(endDateRaw.getTime() + 24 * 60 * 60 * 1000)
      : endDateRaw;

  /** -----------------------------
   * Countdown logic (fixed)
   * ----------------------------- */
  const getCountdownString = () => {
    if (!result || !cheapMode) return "Charging now";
    if (!startDate || !endDate) return "—";

    const now = new Date();

    if (now >= startDate && now <= endDate) {
      return "Charging now";
    }

    if (now > endDate) {
      return "Completed";
    }

    const diffMs = startDate.getTime() - now.getTime();
    const diffMin = Math.floor(diffMs / 60000);

    const hrs = Math.floor(diffMin / 60);
    const mins = diffMin % 60;

    return `${hrs}h ${mins}m`;
  };


  useEffect(() => {
    if (!result) return;

    setCountdown(getCountdownString());

    const timer = setInterval(() => {
      setCountdown(getCountdownString());
    }, 1000);

    return () => clearInterval(timer);
  }, [result, cheapMode]);

  /** -----------------------------
   * Backend call
   * ----------------------------- */
  const handleOptimize = async () => {
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battery_level: battery,
          charger_power: power,
          target_time: departure,
          cheap_mode: cheapMode,
          target_soc: targetSoc,
        }),
      });

      const data: PredictResponse = await res.json();
      if (!res.ok) throw new Error((data as any).error || "Request failed");

      setResult(data);
    } catch (err) {
      alert("⚠️ Error connecting to backend!");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  /** -----------------------------
   * Chart data
   * ----------------------------- */
  const chartData = useMemo(() => {
    if (!result) return [];

    return result.timeline.map((p) => {
      const d = buildDateFromHHMM(p.abs_time);
      return {
        abs: d ? d.getTime() : 0,
        soc: p.soc,
      };
    });
  }, [result]);


  /** -----------------------------
   * Departure indicator
   * ----------------------------- */
  const departureStatus = () => {
    if (!result) return null;

    if (!result.meets_departure) {
      return (
        <div className="text-xs text-yellow-400 mt-1">
          ❗ Cannot reach target SOC before departure time. Consider increasing charger power or lowering target SOC.
        </div>
      );
    }

    return (
      <div className="text-xs text-green-400 mt-1">
        ✔ Charging plan fits perfectly before the selected departure time.
      </div>
    );
  };

  const startTs = startDate ? startDate.getTime() : null;
  const endTs = endDate ? endDate.getTime() : null;


  /** -----------------------------
   * Render
   * ----------------------------- */
  return (
    <main className="min-h-screen bg-background text-foreground p-4 md:p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl md:text-4xl font-bold text-center mb-6 md:mb-8">
          ⚡ Smart EV Charging Optimization
        </h1>
        <ModeToggle />
      </div>

      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-card border-border shadow-md">
          <CardHeader>
            <CardTitle>Charging Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm mb-2 text-muted-foreground">
                Current Battery: <span className="font-semibold">{battery}%</span>
              </label>
              <Slider value={[battery]} min={0} max={100} step={1} onValueChange={(v) => setBattery(v[0])} />
            </div>

            <div>
              <label className="block text-sm mb-2 text-muted-foreground">Charger Power</label>
              <Select value={power.toString()} onValueChange={(v) => setPower(Number(v))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 kW</SelectItem>
                  <SelectItem value="7">7 kW</SelectItem>
                  <SelectItem value="11">11 kW</SelectItem>
                  <SelectItem value="22">22 kW</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm mb-2 text-muted-foreground">
                Target Battery: <span className="font-semibold">{targetSoc}%</span>
              </label>
              <Slider value={[targetSoc]} min={50} max={100} step={1} onValueChange={(v) => setTargetSoc(v[0])} />
            </div>

            <div>
              <label className="block text-sm mb-2 text-muted-foreground">Departure Time</label>
              <input
                type="time"
                value={departure}
                onChange={(e) => setDeparture(e.target.value)}
                className="w-full p-2 rounded-md bg-secondary"
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Optimize by electricity cost</span>
              <Switch checked={cheapMode} onCheckedChange={setCheapMode} />
            </div>

            <Button onClick={handleOptimize} disabled={loading} className="w-full">
              {loading ? "⏳ Optimizing..." : "🔥 Optimize Charging"}
            </Button>

            <p className="text-xs text-muted-foreground">Low-price hours: 22:00–02:00</p>
          </CardContent>
        </Card>

        <Card className="bg-card border-border shadow-md">
          <CardHeader>
            <CardTitle>{cheapMode ? "Optimized Plan" : "Normal Charging"}</CardTitle>
          </CardHeader>

          <CardContent>
            {!result && <p className="text-muted-foreground">No result yet.</p>}

            {result && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between">
                    <span>⏱ Countdown</span>
                    <span className="font-semibold">{countdown}</span>
                  </div>

                  <div className="flex justify-between">
                    <span>🚗 Charging Needed</span>
                    <span className="font-semibold">{result.hours.toFixed(2)}h</span>
                  </div>

                  <div className="flex justify-between">
                    <span>🔋 Final Battery</span>
                    <span className="font-semibold">{result.final_battery}%</span>
                  </div>

                  <div className="flex justify-between">
                    <span>💰 Cost (now)</span>
                    <span>RM {result.cost_now.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between">
                    <span>💸 Cost (optimized)</span>
                    <span>
                      {cheapMode
                        ? `RM ${result.cost_optimized.toFixed(2)}`
                        : `-`}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span>🎯 Savings</span>
                    <span className="text-green-500 font-semibold">
                      {cheapMode
                        ? `RM ${result.savings.toFixed(2)}`
                        : `-`}
                    </span>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    {result.night_tariff_applied
                      ? "Night tariff applied 22:00–02:00"
                      : "No cost optimization applied"}
                  </div>
                </div>

                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <XAxis
                        dataKey="abs"
                        type="number"
                        scale="time"
                        domain={["dataMin", "dataMax"]}
                        tickFormatter={(v) =>
                          new Date(v).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        }
                      />
                      <YAxis domain={[0, 100]} />
                      <Tooltip
                        content={({ label, payload }) => {
                          if (!payload || !payload.length) return null;

                          return (
                            <div className="rounded-md bg-background border p-2 text-xs">
                              <div>
                                ⏰{" "}
                                {new Date(label as number).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </div>
                              <div>🔋 SOC: {payload[0].value}%</div>
                            </div>
                          );
                        }}
                      />

                      {startTs && (
                        <ReferenceLine
                          x={startTs}
                          stroke="#f97316"
                          strokeDasharray="3 3"
                          label={{
                            value: "Start",
                            position: "top",
                            fill: "#f97316",
                            fontSize: 12,
                          }}
                        />
                      )}

                      {endTs && (
                        <ReferenceLine
                          x={endTs}
                          stroke="#06b6d4"
                          strokeDasharray="3 3"
                          label={{
                            value: "End",
                            position: "top",
                            fill: "#06b6d4",
                            fontSize: 12,
                          }}
                        />
                      )}

                      <Line
                        type="monotone"
                        dataKey="soc"
                        stroke={cheapMode ? "#22c55e" : "#3b82f6"}
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <p className="text-xs text-muted-foreground mt-2">
                  Start: {result.start_time} — End: {result.end_time}
                </p>

                {departureStatus()}
              </motion.div>
            )}
          </CardContent>
        </Card>
      </div>

      <footer className="mt-10 text-center text-xs text-muted-foreground">
        © 2025 Smart EV Optimizer — Built by Ricky
      </footer>
    </main>
  );
}
