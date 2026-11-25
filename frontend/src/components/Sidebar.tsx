import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  deleteConversation,
  listConversations,
  renameConversation,
  type Conversation,
} from "../lib/api";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

type SidebarProps = {
  hidden: boolean;
  showClose?: boolean;
  onClose?: () => void;
};

function mergeTitleDrafts(
  rows: Conversation[],
  prevConv: Conversation[],
  prevTitles: Record<string, string>,
  focusedId: string | null,
): Record<string, string> {
  const next = { ...prevTitles };
  for (const row of rows) {
    const lastServer = prevConv.find((c) => c.id === row.id)?.title ?? row.title;
    const draft = prevTitles[row.id] ?? lastServer;
    if (focusedId === row.id && draft !== lastServer) {
      next[row.id] = draft;
    } else {
      next[row.id] = row.title;
    }
  }
  return next;
}

export function Sidebar({ hidden, showClose, onClose }: SidebarProps) {
  const { t, lang, setLang } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const focusedTitleIdRef = useRef<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function refresh() {
    try {
      const rows = await listConversations();
      setHistoryError(null);
      setConversations((prevConv) => {
        setTitles((prevTitles) =>
          mergeTitleDrafts(rows, prevConv, prevTitles, focusedTitleIdRef.current),
        );
        return rows;
      });
    } catch (err) {
      if (err instanceof Error && err.message === "Sign in again.") {
        navigate("/");
        return;
      }
      const message = err instanceof Error ? err.message : "Request failed";
      setHistoryError(message);
    }
  }

  useEffect(() => {
    void refresh();
  }, [location.pathname]);

  async function saveTitle(id: string) {
    const title = titles[id]?.trim();
    if (!title) return;
    try {
      const updated = await renameConversation(id, title);
      setConversations((prev) => prev.map((row) => (row.id === id ? updated : row)));
      setTitles((prev) => ({ ...prev, [id]: updated.title }));
    } catch {
      /* keep draft */
    }
  }

  function openDelete(id: string) {
    setDeleteId(id);
    setDeleteError(null);
    dialogRef.current?.showModal();
  }

  async function confirmDelete() {
    if (!deleteId) return;
    setDeleteError(null);
    try {
      await deleteConversation(deleteId);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Request failed");
      return;
    }
    dialogRef.current?.close();
    const removed = deleteId;
    setDeleteId(null);
    setConversations((prev) => prev.filter((row) => row.id !== removed));
    if (location.pathname === `/app/c/${removed}`) {
      navigate("/app");
    }
  }

  return (
    <aside className={hidden ? "sidebar hidden" : "sidebar"}>
      {showClose ? (
        <p>
          <button type="button" onClick={onClose}>
            {t("close")}
          </button>
        </p>
      ) : null}
      <h1>{t("appName")}</h1>
      <p>
        <button type="button" onClick={() => setLang(lang === "en" ? "it" : "en")}>
          {lang === "en" ? "IT" : "EN"}
        </button>
      </p>
      {historyError ? <p role="alert">{historyError}</p> : null}
      <p>
        <Link to="/app">{t("newChat")}</Link>
      </p>
      <ul>
        {conversations.map((row) => (
          <li key={row.id}>
            <Link to={`/app/c/${row.id}`}>{row.title}</Link>
            <p>
              <input
                value={titles[row.id] ?? row.title}
                onFocus={() => {
                  focusedTitleIdRef.current = row.id;
                }}
                onBlur={() => {
                  if (focusedTitleIdRef.current === row.id) {
                    focusedTitleIdRef.current = null;
                  }
                }}
                onChange={(event) =>
                  setTitles((prev) => ({ ...prev, [row.id]: event.target.value }))
                }
              />
              <button type="button" onClick={() => void saveTitle(row.id)}>
                {t("save")}
              </button>
              <button type="button" onClick={() => openDelete(row.id)}>
                {t("delete")}
              </button>
            </p>
          </li>
        ))}
      </ul>
      <p>
        <Link to="/app/sources">{t("sources")}</Link>
      </p>
      <p>
        <Link to="/app/account">{t("account")}</Link>
      </p>
      <p>
        <Link to="/privacy">{t("privacy")}</Link>
      </p>
      <p>
        <button type="button" onClick={() => supabase.auth.signOut()}>
          {t("signOut")}
        </button>
      </p>
      <dialog ref={dialogRef} onClose={() => setDeleteError(null)}>
        <p>{t("deleteChat")}</p>
        {deleteError ? <p role="alert">{deleteError}</p> : null}
        <p>
          <button type="button" onClick={() => dialogRef.current?.close()}>
            {t("cancel")}
          </button>
          <button type="button" onClick={() => void confirmDelete()}>
            {t("delete")}
          </button>
        </p>
      </dialog>
    </aside>
  );
}