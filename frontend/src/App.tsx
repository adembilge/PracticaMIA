import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { I18nProvider } from "./lib/i18n";
import { supabase } from "./lib/supabase";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ForgotPage } from "./pages/ForgotPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { Shell } from "./components/Shell";
import { ChatPage } from "./pages/ChatPage";
import { SourcesPage } from "./pages/SourcesPage";
import { AccountPage } from "./pages/AccountPage";

export function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, []);

  if (session === undefined) return <p>…</p>;

  return (
    <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={session ? <Navigate to="/app" replace /> : <LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot" element={<ForgotPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/app" element={session ? <Shell /> : <Navigate to="/" replace />}>
            <Route index element={<ChatPage />} />
            <Route path="c/:conversationId" element={<ChatPage />} />
            <Route path="sources" element={<SourcesPage />} />
            <Route path="account" element={<AccountPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </I18nProvider>
  );
}