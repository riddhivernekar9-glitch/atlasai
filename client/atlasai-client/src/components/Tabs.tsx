export default function Tabs({
  tab,
  setTab,
}: {
  tab: "answer" | "search";
  setTab: (t: "answer" | "search") => void;
}) {
  return (
    <div className="tabs">
      <button
        className={`btn ${tab === "answer" ? "btnActive" : "btnGhost"}`}
        onClick={() => setTab("answer")}
        type="button"
      >
        Answer
      </button>
      <button
        className={`btn ${tab === "search" ? "btnActive" : "btnGhost"}`}
        onClick={() => setTab("search")}
        type="button"
      >
        Search
      </button>
    </div>
  );
}