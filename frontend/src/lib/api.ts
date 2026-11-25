import { supabase } from "./supabase";

async function authHeader(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Sign in again.");
  return { Authorization: `Bearer ${token}` };
}

async function readError(response: Response): Promise<never> {
  const body = await response.json();
  const detail = body.detail;
  const message =
    typeof detail === "object" && detail !== null && "message" in detail
      ? String(detail.message)
      : body.message;
  throw new Error(message ?? "Request failed");
}

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};
export type Citation = {
  chunk_id: string;
  title: string;
  url: string;
  heading: string;
  fetched_at: string;
};
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
};

export async function deleteAccount(): Promise<void> {
  const response = await fetch("/api/account", { method: "DELETE", headers: await authHeader() });
  if (response.status === 204) return;
  await readError(response);
}

export async function listConversations(): Promise<Conversation[]> {
  const response = await fetch("/api/conversations", { headers: await authHeader() });
  if (!response.ok) await readError(response);
  return response.json();
}

export async function createConversation(title: string): Promise<Conversation> {
  const response = await fetch("/api/conversations", {
    method: "POST",
    headers: { ...(await authHeader()), "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) await readError(response);
  return response.json();
}

export async function renameConversation(id: string, title: string): Promise<Conversation> {
  const response = await fetch(`/api/conversations/${id}`, {
    method: "PATCH",
    headers: { ...(await authHeader()), "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) await readError(response);
  return response.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(`/api/conversations/${id}`, {
    method: "DELETE",
    headers: await authHeader(),
  });
  if (response.status === 204) return;
  if (!response.ok) await readError(response);
}

export async function listMessages(conversationId: string): Promise<ChatMessage[]> {
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
    headers: await authHeader(),
  });
  if (!response.ok) await readError(response);
  return response.json();
}

export async function postMessage(conversationId: string, content: string): Promise<ChatMessage> {
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { ...(await authHeader()), "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) await readError(response);
  return response.json();
}