import { useEffect, useState } from "react";
import DocumentUploader from "./DocumentUploader";
import { getHealth } from "./api";

export default function App() {
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((s) => !cancelled && setStatus(s))
      .catch(() => !cancelled && setStatus("unreachable"));
    return () => {
      cancelled = true;
    };
  }, []);

  const ok = status === "ok";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">DocuAsk</h1>
            <p className="text-xs text-slate-500">Upload a document, ask questions</p>
          </div>
          <div
            className="flex items-center gap-2 text-xs text-slate-500"
            title={`API status: ${status}`}
          >
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${
                status === "loading"
                  ? "animate-pulse bg-amber-400"
                  : ok
                  ? "bg-emerald-500"
                  : "bg-red-500"
              }`}
              aria-hidden="true"
            />
            API {status}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-md px-6 py-10">
        <h2 className="mb-1 text-lg font-semibold">Add a document</h2>
        <p className="mb-5 text-sm text-slate-500">
          Upload a PDF or paste text. We extract and index it so you can ask
          questions about it.
        </p>
        <DocumentUploader onReady={(doc) => console.log("ready", doc)} />
      </main>
    </div>
  );
}
