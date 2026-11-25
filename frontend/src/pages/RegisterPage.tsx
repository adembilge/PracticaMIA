import { FormEvent, useState } from "react";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

export function RegisterPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showBadCredentials, setShowBadCredentials] = useState(false);
  const [showCheckEmail, setShowCheckEmail] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setShowBadCredentials(false);
    setShowCheckEmail(false);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setShowBadCredentials(true);
      return;
    }
    setShowCheckEmail(true);
  }

  return (
    <section>
      {showCheckEmail ? (
        <p>{t("checkEmail")}</p>
      ) : (
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
              autoComplete="new-password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              required
            />
          </p>
          {showBadCredentials ? <p>{t("badCredentials")}</p> : null}
          <button type="submit" className="seal">
            {t("createAccount")}
          </button>
        </form>
      )}
    </section>
  );
}