import { useI18n } from "../lib/i18n";

export function SourcesPage() {
  const { t } = useI18n();
  return (
    <section>
      <p>{t("noSources")}</p>
    </section>
  );
}