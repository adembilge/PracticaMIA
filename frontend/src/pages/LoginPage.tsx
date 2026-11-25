import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

export function LoginPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showBadCredentials, setShowBadCredentials] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setShowBadCredentials(false);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setShowBadCredentials(true);
  }

  return (
    <section>
      <form onSubmit={onSubmit}>
        <p>
          <label htmlFor="email">{t("email")}</label>
          <input
            id="email"
            type="email"
            name="email"
            autoComplete="email"
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            required
          />
        </p>
        <p>
          <label htmlFor="password">{t("password")}</label>
          <input
            id="password"
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
            required
          />
        </p>
        {showBadCredentials ? <p>{t("badCredentials")}</p> : null}
        <button type="submit" className="seal">
          {t("signIn")}
        </button>
      </form>
      <p>
        <Link to="/register">{t("createAccount")}</Link>
      </p>
      <p>
        <Link to="/forgot">{t("forgot")}</Link>
      </p>
      <p>
        <Link to="/privacy">{t("privacy")}</Link>
      </p>
    </section>
  );
}