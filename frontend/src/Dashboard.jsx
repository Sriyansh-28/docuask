import { useCallback, useEffect, useState } from "react";
import { getStats } from "./api";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setStats(await getStats());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !stats) {
    return <p className="py-10 text-center text-sm text-slate-400">Loading metrics…</p>;
  }
  if (error) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
        Could not load stats ({error}).
      </div>
    );
  }

  const upRate =
    stats.thumbs_up_rate === null ? "—" : `${Math.round(stats.thumbs_up_rate * 100)}%`;
  const median =
    stats.median_latency_ms === null ? "—" : `${stats.median_latency_ms} ms`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Metrics</h2>
        <button
          onClick={load}
          className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 ring-1 ring-slate-200 transition hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Questions" value={stats.total_questions} />
        <StatCard label="Median latency" value={median} />
        <StatCard
          label="Thumbs-up rate"
          value={upRate}
          hint={
            stats.thumbs_up + stats.thumbs_down > 0
              ? `${stats.thumbs_up}/${stats.thumbs_up + stats.thumbs_down} rated`
              : "no ratings yet"
          }
        />
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-lg ring-1 ring-slate-200">
        <h3 className="text-sm font-semibold text-slate-700">Questions over time</h3>
        <QuestionsBarChart data={stats.questions_over_time} />
      </div>
    </div>
  );
}

function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-lg ring-1 ring-slate-200">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold tabular-nums text-slate-800">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function QuestionsBarChart({ data }) {
  const [hover, setHover] = useState(null);

  if (!data || data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-400">
        No questions asked yet.
      </p>
    );
  }

  const max = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="mt-4">
      {/* Plot area: bars anchored to a baseline, rounded tops, gaps between. */}
      <div className="relative flex h-40 items-end gap-2 border-b border-slate-200">
        {data.map((d) => (
          <div
            key={d.date}
            className="group relative flex h-full flex-1 items-end justify-center"
            onMouseEnter={() => setHover(d.date)}
            onMouseLeave={() => setHover(null)}
          >
            {hover === d.date && (
              <div className="absolute -top-9 z-10 whitespace-nowrap rounded-md bg-slate-800 px-2 py-1 text-xs text-white shadow">
                {d.count} on {d.date}
              </div>
            )}
            <div
              className="w-full max-w-[2.5rem] rounded-t bg-emerald-500 transition group-hover:bg-emerald-600"
              style={{ height: `${(d.count / max) * 100}%` }}
              aria-label={`${d.count} questions on ${d.date}`}
            />
          </div>
        ))}
      </div>
      {/* X axis: show first and last date to avoid crowding. */}
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>{data[0].date}</span>
        {data.length > 1 && <span>{data[data.length - 1].date}</span>}
      </div>
    </div>
  );
}
