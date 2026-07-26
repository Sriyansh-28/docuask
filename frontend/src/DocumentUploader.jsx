import { useCallback, useRef, useState } from "react";
import { uploadFile, uploadText } from "./api";

const MAX_MB = 10;

// UI state machine: idle → uploading → (ready | error), with error/ready
// returning to idle on a new attempt.
const IDLE = "idle";
const UPLOADING = "uploading";
const READY = "ready";
const ERROR = "error";

export default function DocumentUploader({ onReady }) {
  const [state, setState] = useState(IDLE);
  const [error, setError] = useState(null);
  const [doc, setDoc] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState("file"); // "file" | "text"
  const [text, setText] = useState("");
  const inputRef = useRef(null);

  const submit = useCallback(
    async (promise) => {
      setState(UPLOADING);
      setError(null);
      try {
        const payload = await promise;
        setDoc(payload);
        setState(READY);
        onReady?.(payload);
      } catch (err) {
        setError(err.message);
        setState(ERROR);
      }
    },
    [onReady],
  );

  const handleFile = useCallback(
    (file) => {
      if (!file) return;
      const isPdf =
        file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      if (!isPdf) {
        setError("Only PDF files are supported.");
        setState(ERROR);
        return;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`File is too large (max ${MAX_MB} MB).`);
        setState(ERROR);
        return;
      }
      submit(uploadFile(file));
    },
    [submit],
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      handleFile(e.dataTransfer.files?.[0]);
    },
    [handleFile],
  );

  const reset = () => {
    setState(IDLE);
    setError(null);
    setDoc(null);
    setText("");
  };

  if (state === READY && doc) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow-lg ring-1 ring-slate-200">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            ✓
          </span>
          <div className="min-w-0">
            <h2 className="font-semibold text-slate-800">Document ready</h2>
            <p className="mt-1 truncate text-sm text-slate-500">
              {doc.filename || "Pasted text"}
            </p>
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
              <dt className="text-slate-400">Chunks</dt>
              <dd className="text-right font-medium tabular-nums">{doc.num_chunks}</dd>
              <dt className="text-slate-400">Characters</dt>
              <dd className="text-right font-medium tabular-nums">
                {doc.num_chars.toLocaleString()}
              </dd>
            </dl>
            <p className="mt-3 break-all font-mono text-xs text-slate-400">
              id: {doc.document_id}
            </p>
          </div>
        </div>
        <button
          onClick={reset}
          className="mt-5 w-full rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
        >
          Upload another
        </button>
      </div>
    );
  }

  const busy = state === UPLOADING;

  return (
    <div className="rounded-2xl bg-white p-6 shadow-lg ring-1 ring-slate-200">
      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-sm">
        <button
          onClick={() => setMode("file")}
          disabled={busy}
          className={`flex-1 rounded-md px-3 py-1.5 font-medium transition ${
            mode === "file" ? "bg-white shadow-sm text-slate-800" : "text-slate-500"
          }`}
        >
          Upload PDF
        </button>
        <button
          onClick={() => setMode("text")}
          disabled={busy}
          className={`flex-1 rounded-md px-3 py-1.5 font-medium transition ${
            mode === "text" ? "bg-white shadow-sm text-slate-800" : "text-slate-500"
          }`}
        >
          Paste text
        </button>
      </div>

      {mode === "file" ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={busy ? (e) => e.preventDefault() : onDrop}
          onClick={() => !busy && inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && !busy) inputRef.current?.click();
          }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-emerald-400 bg-emerald-50"
              : "border-slate-300 bg-slate-50 hover:border-slate-400"
          } ${busy ? "pointer-events-none opacity-60" : ""}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          {busy ? (
            <>
              <span className="h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
              <p className="mt-3 text-sm text-slate-500">Parsing…</p>
            </>
          ) : (
            <>
              <span className="text-3xl">📄</span>
              <p className="mt-2 text-sm font-medium text-slate-700">
                Drag a PDF here, or click to browse
              </p>
              <p className="mt-1 text-xs text-slate-400">PDF up to {MAX_MB} MB</p>
            </>
          )}
        </div>
      ) : (
        <div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
            rows={7}
            placeholder="Paste the document text here…"
            className="w-full resize-y rounded-xl border border-slate-300 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-slate-400 focus:bg-white disabled:opacity-60"
          />
          <button
            onClick={() => submit(uploadText(text))}
            disabled={busy || !text.trim()}
            className="mt-3 w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {busy ? "Parsing…" : "Ingest text"}
          </button>
        </div>
      )}

      {state === ERROR && error && (
        <div className="mt-4 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
          <span aria-hidden="true">⚠</span>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
