import { useEffect, useState } from "react";

// In dev, requests go to "/api/*" and Vite proxies them to the backend.
// In production, set VITE_API_URL to the deployed backend origin.
const API_BASE = import.meta.env.VITE_API_URL || "/api";

export default function App() {
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setStatus(data.status);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("unreachable");
          setError(err.message);
        }
      }
    }

    checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const ok = status === "ok";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-lg ring-1 ring-slate-200 p-8">
        <h1 className="text-2xl font-bold tracking-tight">DocuAsk</h1>
        <p className="mt-1 text-sm text-slate-500">
          Full-stack document Q&amp;A — skeleton
        </p>

        <div className="mt-6 flex items-center gap-3 rounded-lg bg-slate-50 px-4 py-3 ring-1 ring-slate-200">
          <span
            className={`inline-block h-3 w-3 rounded-full ${
              status === "loading"
                ? "bg-amber-400 animate-pulse"
                : ok
                ? "bg-emerald-500"
                : "bg-red-500"
            }`}
            aria-hidden="true"
          />
          <span className="font-medium">
            API status:{" "}
            <span className={ok ? "text-emerald-600" : "text-slate-700"}>
              {status}
            </span>
          </span>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600">
            Could not reach the backend ({error}). Is it running?
          </p>
        )}
      </div>
    </div>
  );
}
