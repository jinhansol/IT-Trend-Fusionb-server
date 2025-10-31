import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";

const LANGUAGE_COLORS = {
  Python: "#3572A5",
  TypeScript: "#3178C6",
  JavaScript: "#F7DF1E",
  Java: "#b07219",
  "C++": "#00599C",
  Markdown: "#083fa1",
  N_A: "#a0aec0",
};

export default function GithubChart({ data }) {
  if (!data || data.length === 0)
    return <p className="text-gray-400 text-center text-sm">데이터를 불러오는 중...</p>;

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip
          cursor={{ fill: "#f3f4f6" }}
          contentStyle={{ backgroundColor: "white", borderRadius: "8px" }}
        />
        <Bar dataKey="usage" radius={[6, 6, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={LANGUAGE_COLORS[entry.name] || "#60A5FA"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
