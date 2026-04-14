import { useState } from "react";
import type { IngestResponse } from "../api";
import { open } from "@tauri-apps/plugin-dialog";

export default function IngestPanel({
  ingesting,
  status,
  result,
  onIngest,
}: {
  ingesting: boolean;
  status: string | null;
  result: IngestResponse | null;
  onIngest: (path: string) => void;
}) {
  const [path, setPath] = useState("");

  function normalizePath(p: string) {
    return p.replace(/\r?\n/g, "");
  }

  async function chooseFolder() {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected === "string" && selected.length > 0) {
      setPath(normalizePath(selected));
    }
  }

  async function chooseFile() {
    const selected = await open({ directory: false, multiple: false });
    if (typeof selected === "string" && selected.length > 0) {
      setPath(normalizePath(selected));
    }
  }

  function runIngest() {
    const p = normalizePath(path);
    if (p.length === 0) return;
    onIngest(p);
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <div className="panelTitle">INGEST</div>
        <div className="panelSubtitle">
          Choose a folder (recommended) or a file, ingest, then query it.
        </div>
      </div>

      <div className="label">Path</div>
      <input
        className="inputWide"
        value={path}
        onChange={(e) => setPath(e.target.value)}
        placeholder="Choose a folder or file..."
      />

      <div className="row" style={{ marginTop: 14, flexWrap: "wrap", gap: 12 }}>
        <button className="btnSecondary" onClick={chooseFolder} disabled={ingesting}>
          Choose Folder…
        </button>

        <button className="btnSecondary" onClick={chooseFile} disabled={ingesting}>
          Choose File…
        </button>

        <div style={{ flex: 1 }} />

        <button
          className="btnPrimary"
          onClick={runIngest}
          disabled={ingesting || normalizePath(path).length === 0}
        >
          {ingesting ? "Ingesting…" : "Ingest"}
        </button>
      </div>

      {status && (
        <div style={{ marginTop: 16 }}>
          <div className="muted">{status}</div>
        </div>
      )}

      {result && (
        <pre className="resultBox" style={{ marginTop: 14 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </section>
  );
}