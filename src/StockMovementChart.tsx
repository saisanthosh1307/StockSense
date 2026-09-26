import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ChartPoint = {
  date: string;
  received: number;
  shipped: number;
};

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <span key={item.name}>
          <i style={{ background: item.color }} />
          {item.name}
          <b>{item.value}</b>
        </span>
      ))}
    </div>
  );
}

export default function StockMovementChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="receivedFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4d9673" stopOpacity={0.17} />
              <stop offset="100%" stopColor="#4d9673" stopOpacity={0.005} />
            </linearGradient>
            <linearGradient id="shippedFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#e0a956" stopOpacity={0.12} />
              <stop offset="100%" stopColor="#e0a956" stopOpacity={0.005} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="#e9eeea" strokeDasharray="3 5" />
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#89938e", fontSize: 11 }}
            dy={9}
          />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: "#89938e", fontSize: 11 }} />
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="received"
            name="Received"
            stroke="#478c6a"
            strokeWidth={2.4}
            fill="url(#receivedFill)"
            activeDot={{ r: 4, fill: "#478c6a", stroke: "#fff", strokeWidth: 2 }}
          />
          <Area
            type="monotone"
            dataKey="shipped"
            name="Shipped"
            stroke="#d9a04d"
            strokeWidth={2.2}
            fill="url(#shippedFill)"
            activeDot={{ r: 4, fill: "#d9a04d", stroke: "#fff", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}