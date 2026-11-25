import { createContext, useContext, useMemo, useState } from "react";

type Lang = "en" | "it";
const KEY = "practica.lang";

const copy: Record<string, { en: string; it: string }> = {
  appName: { en: "PracticaMIA", it: "PracticaMIA" },
  signIn: { en: "Sign in", it: "Entra" },
  createAccount: { en: "Create account", it: "Crea un account" },
  email: { en: "Email", it: "Email" },
  password: { en: "Password", it: "Password" },
  forgot: { en: "Forgot password", it: "Password dimenticata" },
  signOut: { en: "Sign out", it: "Esci" },
  newChat: { en: "New chat", it: "Nuova chat" },
  sources: { en: "Official sources", it: "Fonti ufficiali" },
  account: { en: "Account", it: "Account" },
  privacy: { en: "Privacy", it: "Privacy" },
  deleteAccount: { en: "Delete account", it: "Elimina account" },
  deleteConfirm: {
    en: "This deletes your chats.",
    it: "Questo elimina le tue chat.",
  },
  send: { en: "Send", it: "Invia" },
  emptyChat: {
    en: "Ask about an Italian public procedure.",
    it: "Chiedi di una procedura della pubblica amministrazione.",
  },
  noSources: {
    en: "No official pages indexed yet.",
    it: "Nessuna pagina ufficiale indicizzata.",
  },
  quota: {
    en: "The daily answer capacity is used. Try again tomorrow.",
    it: "La capacità giornaliera di risposte è esaurita. Riprova domani.",
  },
  disclaimer: {
    en: "PracticaMIA explains published official procedures. It is not a lawyer, a patronato, or a questura. Check the linked page.",
    it: "PracticaMIA spiega procedure ufficiali pubblicate. Non è un avvocato, un patronato o una questura. Controlla la pagina collegata.",
  },
  privacyBody: {
    en: "Do not paste a permit number, codice fiscale, passport number, or a photo of a document. Chats are stored in the EU Supabase project. Deleting the account deletes the chats.",
    it: "Non incollare numero di permesso, codice fiscale, numero di passaporto o foto di un documento. Le chat restano nel progetto Supabase nell'UE. Eliminare l'account elimina le chat.",
  },
  apiDown: { en: "API unreachable", it: "API non raggiungibile" },
  checkEmail: { en: "Check your email", it: "Controlla l'email" },
  badCredentials: {
    en: "Check the email and password.",
    it: "Controlla email e password.",
  },
  cancel: { en: "Cancel", it: "Annulla" },
  menu: { en: "Menu", it: "Menu" },
  close: { en: "Close", it: "Chiudi" },
};

const I18nContext = createContext<{
  lang: Lang;
  t: (key: string) => string;
  setLang: (lang: Lang) => void;
} | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const stored = localStorage.getItem(KEY);
  const initial: Lang = stored === "it" ? "it" : "en";
  const [lang, setLangState] = useState<Lang>(initial);
  const value = useMemo(
    () => ({
      lang,
      t: (key: string) => copy[key]?.[lang] ?? key,
      setLang: (next: Lang) => {
        localStorage.setItem(KEY, next);
        setLangState(next);
      },
    }),
    [lang],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("I18nProvider missing");
  return value;
}