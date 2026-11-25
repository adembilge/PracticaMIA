import { supabase } from "./supabase";

async function authHeader(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Sign in again.");
  return { Authorization: `Bearer ${token}` };
}

export async function deleteAccount(): Promise<void> {
  const response = await fetch("/api/account", { method: "DELETE", headers: await authHeader() });
  if (response.status === 204) return;
  const body = await response.json();
  throw new Error(body.message ?? "Request failed");
}