import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Composer } from "../components/Composer";
import { MessageList } from "../components/MessageList";
import {
  createConversation,
  listMessages,
  streamMessage,
  type ChatMessage,
} from "../lib/api";
import { useI18n } from "../lib/i18n";

const EXAMPLES: Record<"en" | "it", string[]> = {
  en: [
    "How do I renew a residence permit?",
    "How do I change my registered address?",
    "How do I apply for Italian citizenship by residence?",
  ],
  it: [
    "Come rinnovo il permesso di soggiorno?",
    "Come cambio residenza?",
    "Come chiedo la cittadinanza per residenza?",
  ],
};

export function ChatPage() {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const flight = useRef(0);
  const conversationRef = useRef(conversationId);
  conversationRef.current = conversationId;

  useEffect(() => {
    flight.current += 1;
    sendingRef.current = false;
    setSending(false);
    if (!conversationId) {
      setMessages([]);
      setLoadError(null);
      return;
    }
    setMessages([]);
    setLoadError(null);
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

  async function submit(content: string) {
    const trimmed = content.trim();
    if (!trimmed || !conversationId || sendingRef.current || loading || loadError) return;
    const requestConversation = conversationId;
    const ticket = flight.current + 1;
    flight.current = ticket;
    sendingRef.current = true;
    setSending(true);
    const stamp = Date.now();
    const assistantId = `pending-assistant-${stamp}`;
    setMessages((prev) => [
      ...prev,
      { id: `pending-user-${stamp}`, role: "user", content: trimmed, citations: [] },
      { id: assistantId, role: "assistant", content: "", citations: [] },
    ]);

    function stillHere() {
      return conversationRef.current === requestConversation && flight.current === ticket;
    }

    function replaceAssistant(text: string) {
      if (!stillHere()) return;
      setMessages((prev) =>
        prev.map((row) => (row.id === assistantId ? { ...row, content: text } : row)),
      );
    }

    try {
      await streamMessage(
        requestConversation,
        trimmed,
        {
          onToken: (text) => {
            if (!stillHere()) return;
            setMessages((prev) =>
              prev.map((row) =>
                row.id === assistantId ? { ...row, content: row.content + text } : row,
              ),
            );
          },
          onCitations: (items) => {
            if (!stillHere()) return;
            setMessages((prev) =>
              prev.map((row) => (row.id === assistantId ? { ...row, citations: items } : row)),
            );
          },
          onDone: () => {},
          onError: (code, message) => {
            if (code === "quota_user" || code === "quota_global") replaceAssistant(t("quota"));
            else replaceAssistant(message);
          },
        },
        lang,
      );
    } catch (err) {
      if (err instanceof Error && err.message === "Sign in again.") {
        navigate("/");
        return;
      }
      replaceAssistant(err instanceof Error ? err.message : "API unreachable");
    } finally {
      if (flight.current === ticket) {
        sendingRef.current = false;
        setSending(false);
      }
    }
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
  const examples = EXAMPLES[lang];

  return (
    <section>
      {loadError ? <p role="alert">{loadError}</p> : null}
      <MessageList messages={messages} />
      {messages.length === 0 && loadError === null && !loading ? (
        <p>
          {examples.map((question) => (
            <button
              key={question}
              type="button"
              className="seal"
              disabled={sending}
              onClick={() => void submit(question)}
            >
              {question}
            </button>
          ))}
        </p>
      ) : null}
      <p className="disclaimer">{t("disclaimer")}</p>
      <Composer disabled={composerBlocked || sending} onSubmit={(content) => void submit(content)} />
    </section>
  );
}
