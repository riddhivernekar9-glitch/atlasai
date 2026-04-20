import { useEffect, useMemo, useState } from "react";
import type { AnswerResponse, SearchResponse } from "../api";

type ApiResult = AnswerResponse | SearchResponse;

function baseName(p: string) {
  const parts = p.split(/[\\/]/);
  return parts[parts.length - 1] || p;
}

function tagStyle(tag: string) {
  const t = (tag || "").toLowerCase();

  if (t === "contract") {
    return { background: "rgba(70,120,255,0.18)", border: "1px solid rgba(70,120,255,0.35)" };
  }
  if (t === "visa") {
    return { background: "rgba(255,180,70,0.18)", border: "1px solid rgba(255,180,70,0.35)" };
  }
  if (t === "payroll") {
    return { background: "rgba(80,255,170,0.14)", border: "1px solid rgba(80,255,170,0.35)" };
  }
  if (t === "insurance") {
    return { background: "rgba(255,120,200,0.14)", border: "1px solid rgba(255,120,200,0.35)" };
  }
  if (t === "compliance") {
    return { background: "rgba(255,90,90,0.14)", border: "1px solid rgba(255,90,90,0.35)" };
  }

  return { background: "rgba(255,255,255,0.10)", border: "1px solid rgba(255,255,255,0.18)" };
}

export default function ResultPanel({
  error,
  data,
  loading,
}: {
  error: string | null;
  data: ApiResult | null;
  loading: boolean;
}) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const answerSources = useMemo(() => {
    if (!data || !("answer" in data)) return [];
    return data.sources || [];
  }, [data]);

  const structured = useMemo(() => {
    if (!data || !("answer" in data)) return {};
    return data.structured || {};
  }, [data]);

  const confidence = useMemo(() => {
    if (!data || !("answer" in data)) return {};
    return data.confidence || {};
  }, [data]);

  const groupedSources = useMemo(() => {
    const map = new Map<
      string,
      { key: string; bestScore: number; count: number; sample: any; docType: string }
    >();

    for (const s of answerSources as any[]) {
      const key = (s.path || s.relative_path || "").toString();
      if (!key) continue;

      const prev = map.get(key);
      const score = Number(s.score ?? 0);
      const docType = (s.doc_type && s.doc_type !== "" ? s.doc_type : "General").toString();

      if (!prev) {
        map.set(key, { key, bestScore: score, count: 1, sample: s, docType });
      } else {
        prev.count += 1;
        if (score > prev.bestScore) {
          prev.bestScore = score;
          prev.sample = s;
          prev.docType = docType;
        }
      }
    }

    return Array.from(map.values()).sort((a, b) => b.bestScore - a.bestScore);
  }, [answerSources]);

  const bestSource = groupedSources.length ? groupedSources[0] : null;

  useEffect(() => {
    if (bestSource) {
      const fullPath = (bestSource.sample?.path || bestSource.key || "").toString();
      if (fullPath) setSelectedPath(fullPath);
    } else {
      setSelectedPath(null);
    }
  }, [bestSource]);

  const previewUrl = useMemo(() => {
    if (!selectedPath) return null;
    return `http://127.0.0.1:8000/api/file?path=${encodeURIComponent(selectedPath)}`;
  }, [selectedPath]);

  const hasStructured = Object.keys(structured).length > 0;

  return (
    <section className="panel">
      <div className="panelHeader">
        <div className="panelTitle">RESULT</div>
        <div className="panelSubtitle">Ask a question and review the best matching document.</div>
      </div>

      {loading && <div className="muted">Loading…</div>}
      {error && <div className="errorBox">Error: {error}</div>}

      {!loading && !error && data && "answer" in data && (
        <>
          {hasStructured ? (
            <>
              <div className="panelTitle" style={{ marginTop: 6 }}>
                STRUCTURED ANSWER
              </div>
              <div className="resultBox">
                {Object.entries(structured).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: 12 }}>
                    <div style={{ fontWeight: 800 }}>{key}</div>
                    <div style={{ marginTop: 2 }}>{value}</div>
                    {confidence[key] && (
                      <div style={{ fontSize: 12, opacity: 0.7, marginTop: 2 }}>
                        Confidence: {confidence[key]}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="resultAnswer">{data.answer}</div>
          )}

          {bestSource ? (
            <>
              <div className="panelTitle" style={{ marginTop: 14 }}>
                BEST SOURCE
              </div>

              <div className="resultBox" style={{ padding: 0 }}>
                <button
                  onClick={() => {
                    const fullPath = (bestSource.sample?.path || bestSource.key || "").toString();
                    setSelectedPath(fullPath);
                  }}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    padding: "12px 14px",
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    color: "inherit",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <div style={{ fontWeight: 700 }}>
                      {baseName(bestSource.key)}
                    </div>

                    <span
                      style={{
                        ...tagStyle(bestSource.docType),
                        borderRadius: 999,
                        padding: "3px 9px",
                        fontSize: 12,
                        fontWeight: 700,
                      }}
                    >
                      {bestSource.docType || "General"}
                    </span>

                    <span style={{ opacity: 0.8, fontWeight: 600 }}>
                      (best {bestSource.bestScore.toFixed(3)} | matches {bestSource.count})
                    </span>
                  </div>

                  <div style={{ opacity: 0.7, fontSize: 12, marginTop: 4 }}>
                    {(bestSource.sample?.path || bestSource.key || "").toString()}
                  </div>
                </button>
              </div>
            </>
          ) : null}

          {previewUrl && (
            <>
              <div className="panelTitle" style={{ marginTop: 14 }}>
                PREVIEW
              </div>
              <div className="resultBox" style={{ padding: 0, overflow: "hidden" }}>
                <iframe
                  title="preview"
                  src={previewUrl}
                  style={{ width: "100%", height: 650, border: "none" }}
                />
              </div>
            </>
          )}
        </>
      )}

      {!loading && !error && data && "results" in data && (
        <pre className="resultBox">{JSON.stringify(data.results, null, 2)}</pre>
      )}

      {!loading && !error && !data && (
        <div className="muted">Ask a question, or ingest documents first.</div>
      )}
    </section>
  );
}