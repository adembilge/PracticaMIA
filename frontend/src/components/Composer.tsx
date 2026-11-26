import { useState } from "react";
import { useI18n } from "../lib/i18n";

type ComposerProps = {
  disabled?: boolean;
  onSubmit: (content: string) => void;
};

export function Composer({ disabled = false, onSubmit }: ComposerProps) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");

  function send() {
    const content = draft.trim();
    if (!content || disabled) return;
    setDraft("");
    onSubmit(content);
  }

  return (
    <p>
      <textarea
        value={draft}
        rows={3}
        disabled={disabled}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void send();
          }
        }}
      />
      <button type="button" className="seal" disabled={disabled} onClick={() => void send()}>
        {t("send")}
      </button>
    </p>
  );
}
