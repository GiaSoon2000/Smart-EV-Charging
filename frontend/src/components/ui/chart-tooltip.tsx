"use client";

import { useTheme } from "next-themes";

export function ChartTooltip({ active, payload, label }: any) {
  const { theme } = useTheme();

  if (!active || !payload || !payload.length) return null;

  const bg = theme === "dark" ? "#1f2937" : "#ffffff"; // gray-800 / white
  const border = theme === "dark" ? "#374151" : "#e5e7eb"; // gray-700 / gray-200
  const text = theme === "dark" ? "#f9fafb" : "#111827"; // gray-50 / gray-900

  return (
    <div
      style={{
        background: bg,
        border: `1px solid ${border}`,
        padding: "8px 12px",
        borderRadius: "8px",
        color: text,
        fontSize: "12px",
      }}
    >
      <p style={{ margin: 0 }}>{label}</p>
      <p style={{ margin: 0, fontWeight: "bold" }}>
        SoC: {payload[0].value}%
      </p>
    </div>
  );
}
