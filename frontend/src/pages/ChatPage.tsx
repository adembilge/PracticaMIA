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

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const rows = await listMessages(conversationId);
        if (!cancelled) setMessages(rows);
      } catch (err) {
        if (err instanceof Error && err.message === "Sign in again.") {
          navigate("/");
          return;
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [conversationId, navigate]);

  async function startNewChat() {
    if (creating) return;
    setCreating(true);
    try {
      const conv = await createConversation("New chat");
      navigate(`/app/c/${conv.id}`);
    } catch (err) {
      if (err instanceof Error && err.message === "Sign in again.") {
        navigate("/");
      }
    } finally {
      setCreating(false);
    }
  }

  function appendUser(content: string) {
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

  if (!conversationId) {
    return (
      <section>
        <p>{t("emptyChat")}</p>
        <p className="disclaimer">{t("disclaimer")}</p>
        <p>
          <button type="button" className="seal" disabled={creating} onClick={() => void startNewChat()}>
            {t("newChat")}
          </button>
        </p>
      </section>
    );
  }

  return (
    <section>
      <MessageList messages={messages} />
      <p className="disclaimer">{t("disclaimer")}</p>
      <Composer
        conversationId={conversationId}
        onUserMessage={appendUser}
        onAssistantMessage={(message) => setMessages((prev) => [...prev, message])}
        onAuthError={() => navigate("/")}
      />
    </section>
  );
}