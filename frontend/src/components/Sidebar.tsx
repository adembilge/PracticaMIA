import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

type SidebarProps = {
  hidden: boolean;
};

export function Sidebar({ hidden }: SidebarProps) {
  const { t, lang, setLang } = useI18n();

  return (
    <aside className={hidden ? "sidebar hidden" : "sidebar"}>
      <h1>{t("appName")}</h1>
      <p>
        <button type="button" onClick={() => setLang(lang === "en" ? "it" : "en")}>
          {lang === "en" ? "IT" : "EN"}
        </button>
      </p>
      <p>
        <Link to="/app">{t("newChat")}</Link>
      </p>
      <ul />
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
    </aside>
  );
}