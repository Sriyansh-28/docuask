import { useEffect, useState } from "react";
import DocumentUploader from "./DocumentUploader";
import Chat from "./Chat";
import Dashboard from "./Dashboard";
import { getHealth } from "./api";

// Minimal hash routing keeps the dashboard on its own URL (/#/dashboard)
// without pulling in a router dependency.
function useHashRoute() {
  const [route, setRoute] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setRoute(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export default function App() {
  const [status, setStatus] = useState("loading");
  const [doc, setDoc] = useState(null);
  const route = useHashRoute();
  const onDashboard = route.startsWith("#/dashboard");

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
          <div className="flex items-center gap-4">
            <nav className="flex gap-1 text-sm">
              <NavLink href="#/" active={!onDashboard}>
                Chat
              </NavLink>
              <NavLink href="#/dashboard" active={onDashboard}>
                Dashboard
              </NavLink>
            </nav>
            <span
              className="flex items-center gap-1.5 text-xs text-slate-500"
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
              <span className="hidden sm:inline">API {status}</span>
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-xl px-6 py-10">
        {onDashboard ? (
          <Dashboard />
        ) : doc ? (
          <Chat doc={doc} onReset={() => setDoc(null)} />
        ) : (
          <div className="mx-auto max-w-md">
            <h2 className="mb-1 text-lg font-semibold">Add a document</h2>
            <p className="mb-5 text-sm text-slate-500">
              Upload a PDF or paste text. We extract and index it so you can ask
              questions about it.
            </p>
            <DocumentUploader onReady={setDoc} />
          </div>
        )}
      </main>
    </div>
  );
}

function NavLink({ href, active, children }) {
  return (
    <a
      href={href}
      className={`rounded-lg px-3 py-1.5 font-medium transition ${
        active
          ? "bg-slate-100 text-slate-800"
          : "text-slate-500 hover:bg-slate-50"
      }`}
    >
      {children}
    </a>
  );
}
