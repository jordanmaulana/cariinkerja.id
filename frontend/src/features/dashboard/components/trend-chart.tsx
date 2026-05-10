import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";

import type { DashboardStats } from "@/features/dashboard/types";

export function TrendChart({ data }: { data: DashboardStats["trend_30d"] }) {
  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            interval={Math.max(0, Math.floor(data.length / 6) - 1)}
            tickFormatter={(d: string) =>
              new Date(d).toLocaleDateString("id-ID", {
                day: "2-digit",
                month: "short",
              })
            }
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
          <Tooltip
            cursor={{ stroke: "var(--border)" }}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--foreground)",
            }}
            labelFormatter={(d) =>
              typeof d === "string"
                ? new Date(d).toLocaleDateString("id-ID", {
                    day: "2-digit",
                    month: "short",
                  })
                : ""
            }
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke="var(--foreground)"
            strokeWidth={1.75}
            dot={false}
            activeDot={{ r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
