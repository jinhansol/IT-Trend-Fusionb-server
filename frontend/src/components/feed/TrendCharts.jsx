// Trend charts for Home and Dev. Counts come from the server (tagged items in the period).
// Colors: categorical slots 1-5 of the validated reference palette, fixed per series order.
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"];
const BAR = "#2a78d6";
const AXIS = { fontSize: 12, fill: "#52514e" };
const GRID = "#e7e5e4";

function Panel({ title, caption, children }) {
  return (
    <section className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm">
      <h3 className="font-bold">{title}</h3>
      {caption && <p className="text-xs text-slate-500 mb-3">{caption}</p>}
      {children}
    </section>
  );
}

function Empty() {
  return <p className="text-sm text-slate-400 py-10 text-center">이 기간에 집계할 데이터가 없습니다.</p>;
}

/** Horizontal bars, one hue: magnitude only. */
export function RankBars({ title, caption, items }) {
  const height = Math.max(120, items.length * 32);
  return (
    <Panel title={title} caption={caption}>
      {items.length === 0 ? (
        <Empty />
      ) : (
        <div style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={items} layout="vertical" margin={{ left: 8, right: 24 }} barCategoryGap={6}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={96} tick={AXIS} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#f5f5f4" }} formatter={(value) => [`${value}건`, "글 수"]} />
              <Bar dataKey="count" fill={BAR} radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}

const shortDate = (date) => `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}`;

/** Daily mentions of the top technologies, with a table view for exact numbers. */
export function DailyTrend({ report }) {
  const techs = report.daily_technologies;
  const rows = report.daily.map((day) => ({ date: shortDate(day.date), ...day.counts }));
  return (
    <Panel title="일별 기술 언급 기사 수" caption={`최근 ${report.days}일, 언급이 많은 기술 ${techs.length}개 (수집 콘텐츠 기준)`}>
      {techs.length === 0 ? (
        <Empty />
      ) : (
        <>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ left: -16, right: 16, top: 8 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="date" tick={AXIS} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12, color: "#52514e" }} />
                {techs.map((tech, index) => (
                  <Line
                    key={tech.slug}
                    type="monotone"
                    dataKey={tech.slug}
                    name={tech.name}
                    stroke={SERIES[index]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-slate-500">표로 보기</summary>
            <div className="overflow-x-auto mt-2">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-slate-500">
                    <th className="text-left font-semibold py-1 pr-3">날짜</th>
                    {techs.map((t) => (
                      <th key={t.slug} className="text-right font-semibold py-1 px-2">{t.name}</th>
                    ))}
                    <th className="text-right font-semibold py-1 pl-2">전체 글</th>
                  </tr>
                </thead>
                <tbody>
                  {report.daily.map((day) => (
                    <tr key={day.date} className="border-t border-slate-100 text-slate-700">
                      <td className="py-1 pr-3">{day.date}</td>
                      {techs.map((t) => (
                        <td key={t.slug} className="text-right py-1 px-2">{day.counts[t.slug]}</td>
                      ))}
                      <td className="text-right py-1 pl-2">{day.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </Panel>
  );
}
