import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Composer } from "../components/Composer";
import { MessageList } from "../components/MessageList";
import {
  createConversation,
  listMessages,
  type ChatMessage,
} from "../lib/api";
import { useI18n } from "../lib/i18n";

export function ChatPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      setLoadError(null);
      return;
    }
    setMessages([]);
    setLoadError(null);
    setSendError(null);
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const rows = await listMessages(conversationId);
        if (!cancelled) {
          setMessages(rows);
          setLoadError(null);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof Error && err.message === "Sign in again.") {
          navigate("/");
          return;
        }
        if (err instanceof Error && err.message === "Chat not found.") {
          navigate("/app");
          return;
        }
        const message = err instanceof Error ? err.message : "Request failed";
        setLoadError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [conversationId, navigate]);

  async function startNewChat() {
    if (creating) return;
    setCreating(true);
    setCreateError(null);
    try {
      const conv = await createConversation("New chat");
      navigate(`/app/c/${conv.id}`);
    } catch (err) {
      if (err instanceof Error && err.message === "Sign in again.") {
        navigate("/");
        return;
      }
      setCreateError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setCreating(false);
    }
  }

  function appendUser(content: string) {
    setSendError(null);
    setMessages((prev) => [
      ...prev,
      {
        id: `pending-${Date.now()}`,
        role: "user",
        content,
        citations: [],
      },
    ]);
  }

  function rollbackUser(content: string) {
    setMessages((prev) => {
      for (let i = prev.length - 1; i >= 0; i -= 1) {
        const row = prev[i];
        if (row.role === "user" && row.content === content && row.id.startsWith("pending-")) {
          return [...prev.slice(0, i), ...prev.slice(i + 1)];
        }
      }
      return prev;
    });
  }

  if (!conversationId) {
    return (
      <section>
        <p>{t("emptyChat")}</p>
        <p className="disclaimer">{t("disclaimer")}</p>
        {createError ? <p role="alert">{createError}</p> : null}
        <p>
          <button type="button" className="seal" disabled={creating} onClick={() => void startNewChat()}>
            {t("newChat")}
          </button>
        </p>
      </section>
    );
  }

  const composerBlocked = loading || loadError !== null;

  return (
    <section>
      {loadError ? <p role="alert">{loadError}</p> : null}
      <MessageList messages={messages} />
      <p className="disclaimer">{t("disclaimer")}</p>
      {sendError ? <p role="alert">{sendError}</p> : null}
      <Composer
        conversationId={conversationId}
        disabled={composerBlocked}
        onUserMessage={appendUser}
        onAssistantMessage={(message) => {
          setSendError(null);
          setMessages((prev) => [...prev, message]);
        }}
        onSendFailed={(content, error) => {
          rollbackUser(content);
          setSendError(error);
        }}
        onAuthError={() => navigate("/")}
      />
    </section>
  );
}