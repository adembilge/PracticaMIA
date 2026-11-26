import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listSources, type Source } from "../lib/api";
import { useI18n } from "../lib/i18n";

function calendarDate(value: string): string {
  return value.slice(0, 10);
}

export function SourcesPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [sources, setSources] = useState<Source[] | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setSources(await listSources());
      } catch (err) {
        if (err instanceof Error && err.message === "Sign in again.") {
          navigate("/");
          return;
        }
        setSources([]);
      }
    })();
  }, [navigate]);

  const byTopic = useMemo(() => {
    if (!sources?.length) return null;
    const groups = new Map<string, Source[]>();
    for (const row of sources) {
      const list = groups.get(row.topic) ?? [];
      list.push(row);
      groups.set(row.topic, list);
    }
    return groups;
  }, [sources]);

  if (sources === null) {
    return <section />;
  }

  if (sources.length === 0) {
    return (
      <section>
        <p>{t("noSources")}</p>
      </section>
    );
  }

  return (
    <>
      {[...byTopic!.entries()].map(([topic, rows]) => (
        <section key={topic}>
          <h2>{topic}</h2>
          <ul>
            {rows.map((row) => (
              <li key={row.id}>
                <span>{row.name}</span> <span>{row.status}</span>{" "}
                {row.last_crawled_at ? (
                  <time dateTime={row.last_crawled_at}>{calendarDate(row.last_crawled_at)}</time>
                ) : (
                  <span>—</span>
                )}{" "}
                <a href={row.portal_url}>{row.portal_url}</a>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}