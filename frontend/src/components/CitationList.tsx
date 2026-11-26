import type { Citation } from "../lib/api";

type CitationListProps = {
  citations: Citation[];
};

export function CitationList({ citations }: CitationListProps) {
  const visible = citations.filter(
    (citation) => typeof citation?.url === "string" && citation.url.startsWith("https://"),
  );
  if (visible.length === 0) return null;
  return (
    <div>
      {visible.map((citation, index) => (
        <div key={`${citation.url}-${index}`}>
          <p>
            <a href={citation.url} target="_blank" rel="noreferrer">
              {citation.title}
            </a>
          </p>
          {citation.chunk_id === "" ? null : <p>{citation.fetched_at}</p>}
        </div>
      ))}
    </div>
  );
}
