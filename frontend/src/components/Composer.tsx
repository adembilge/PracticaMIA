import { useState } from "react";
import type { ChatMessage } from "../lib/api";
import { postMessage } from "../lib/api";
import { useI18n } from "../lib/i18n";

type ComposerProps = {
  conversationId: string;
  disabled?: boolean;
  onUserMessage: (content: string) => void;
  onAssistantMessage: (message: ChatMessage) => void;
  onSendFailed: (content: string, error: string) => void;
  onAuthError: () => void;
};

export function Composer({
  conversationId,
  disabled = false,
  onUserMessage,
  onAssistantMessage,
  onSendFailed,
  onAuthError,
}: ComposerProps) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    const content = draft.trim();
    if (!content || sending || disabled) return;
    setSending(true);
    onUserMessage(content);
    setDraft("");
    try {
      const assistant = await postMessage(conversationId, content);
      onAssistantMessage(assistant);
    } catch (err) {
      if (err instanceof Error && err.message === "Sign in again.") {
        onAuthError();
        return;
      }
      const message = err instanceof Error ? err.message : "Request failed";
      setDraft(content);
      onSendFailed(content, message);
    } finally {
      setSending(false);
    }
  }

  return (
    <p>
      <textarea
        value={draft}
        rows={3}
        disabled={sending || disabled}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void send();
          }
        }}
      />
      <button
        type="button"
        className="seal"
        disabled={sending || disabled}
        onClick={() => void send()}
      >
        {t("send")}
      </button>
    </p>
  );
}