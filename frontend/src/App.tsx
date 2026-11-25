import { useEffect, useState } from "react";

export function App() {
  const [line, setLine] = useState("…");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((body: { status: string; db: string }) => setLine(`${body.status} / ${body.db}`))
      .catch(() => setLine("API unreachable"));
  }, []);

  return (
    <main>
      <h1>PracticaMIA</h1>
      <p>{line}</p>
    </main>
  );
}
