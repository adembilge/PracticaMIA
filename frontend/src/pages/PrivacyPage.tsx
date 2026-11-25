import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";

export function PrivacyPage() {
  const { t } = useI18n();
  return (
    <section>
      <p>
        <Link to="/">{t("signIn")}</Link>
      </p>
      <article>
        <p>{t("privacyBody")}</p>
      </article>
    </section>
  );
}