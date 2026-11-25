import { useState } from "react";
import type { ChatMessage } from "../lib/api";
import { postMessage } from "../lib/api";
import { useI18n } from "../lib/i18n";

type ComposerProps = {
  conversationId: string;
  onUserMessage: (content: string) => void;
  onAssistantMessage: (message: ChatMessage) => void;
  onAuthError: () => void;
};

export function Composer({
  conversationId,
  onUserMessage,
  onAssistantMessage,
  onAuthError,
}: ComposerProps) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    const content = draft.trim();
    if (!content || sending) return;
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
      setDraft(content);
    } finally {
      setSending(false);
    }
  }

  return (
    <p>
      <textarea
        value={draft}
        rows={3}
        disabled={sending}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void send();
          }
        }}
      />
      <button type="button" className="seal" disabled={sending} onClick={() => void send()}>
        {t("send")}
      </button>
    </p>
  );
}