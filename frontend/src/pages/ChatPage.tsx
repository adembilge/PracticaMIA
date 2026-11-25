import { useI18n } from "../lib/i18n";

export function ChatPage() {
  const { t } = useI18n();
  return (
    <section>
      <p>{t("emptyChat")}</p>
      <p className="disclaimer">{t("disclaimer")}</p>
    </section>
  );
}