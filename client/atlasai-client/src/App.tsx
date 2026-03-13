import { useState } from "react";
import "./App.css";

import { apiAnswer, apiIngest, type AnswerResponse, type IngestResponse } from "./api";
import ResultPanel from "./components/ResultPanel";
import IngestPanel from "./components/IngestPanel";

export default function App() {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(3);

  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnswerResponse | null>(null);

  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);

  async function runAnswer() {
    setLoading(true);
    setError(null);

    try {
      const json = await apiAnswer(query, Number(limit) || 3);
      setData(json);
    } catch (e: any) {
      setError(e?.message || "Unknown error");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  async function runIngest(path: string) {
    setIngesting(true);
    setIngestStatus(null);
    setIngestResult(null);

    try {
      const json = await apiIngest(path);
      setIngestResult(json);

      if (json.ok) {
        setIngestStatus("Ingest complete ✅");
      } else {
        setIngestStatus(`Ingest failed ❌: ${json.error || "Unknown error"}`);
      }
    } catch (e: any) {
      setIngestStatus(`Ingest failed ❌: ${e?.message || "Unknown error"}`);
    } finally {
      setIngesting(false);
    }
  }

  return (
    <main className="container">
      <header className="topHeader">
        <div>
          <h1 className="title">AtlasAI</h1>
          <div className="subtitle">Local document intelligence</div>
        </div>
        <div className="pill">Local</div>
      </header>

      <section className="panel">
        <div className="panelHeader">
          <div className="panelTitle">ASK</div>
          <div className="panelSubtitle">
            Ask naturally (e.g. “Who is the sponsor?”). The app will search your local documents and extract the best answer.
          </div>
        </div>

        <label className="label">Question / Query</label>
        <textarea
          className="textarea"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question..."
        />

        <div className="row">
          <div className="field">
            <div className="labelSmall">Limit</div>
            <input
              className="input"
              type="number"
              min={1}
              max={20}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            />
          </div>

          <button className="btnPrimary" onClick={runAnswer} disabled={loading || !query.trim()}>
            {loading ? "Working…" : "Get Answer"}
          </button>
        </div>
      </section>

      {/* ✅ Single Result panel */}
      <ResultPanel error={error} data={data} loading={loading} />

      {/* ✅ Ingest panel */}
      <IngestPanel ingesting={ingesting} status={ingestStatus} result={ingestResult} onIngest={runIngest} />
    </main>
  );
}