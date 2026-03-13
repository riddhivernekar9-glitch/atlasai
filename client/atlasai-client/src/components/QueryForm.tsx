import { useEffect } from "react";

export default function QueryForm({
  tab,
  query,
  setQuery,
  limit,
  setLimit,
  loading,
  onRun,
}: {
  tab: "answer" | "search";
  query: string;
  setQuery: (v: string) => void;
  limit: number;
  setLimit: (n: number) => void;
  loading: boolean;
  onRun: () => void;
}) {
  useEffect(() => {
    // Optional: keep limit sane
    if (!limit || limit < 1) setLimit(3);
  }, [limit, setLimit]);

  const buttonLabel = tab === "answer" ? "Get Answer" : "Search Docs";

  return (
    <section className="panel">
      <div className="panelHeader">
        <div className="panelTitle">ASK</div>
        <div className="panelSubtitle">Returns a short extracted answer (no long paste).</div>
      </div>

      <label className="label">Question / Query</label>

      <textarea
        className="textarea"
        placeholder="Ask a question..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        rows={4}
      />

      <div className="row">
        <div>
          <div className="label" style={{ marginBottom: 6 }}>
            Limit
          </div>
          <input
            className="input"
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{ width: 110 }}
          />
        </div>

        <button className="btn btnPrimary" onClick={onRun} disabled={loading || !query.trim()} type="button">
          {loading ? "Working…" : buttonLabel}
        </button>
      </div>
    </section>
  );
}