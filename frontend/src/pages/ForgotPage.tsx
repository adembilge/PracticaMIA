import { FormEvent, useState } from "react";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

export function ForgotPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [showCheckEmail, setShowCheckEmail] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setShowCheckEmail(false);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin,
    });
    if (!error) setShowCheckEmail(true);
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
          <button type="submit" className="seal">
            {t("forgot")}
          </button>
        </form>
      )}
    </section>
  );
}