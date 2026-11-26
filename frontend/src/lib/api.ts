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

export async function streamMessage(
  id: string,
  content: string,
  handlers: {
    onToken: (text: string) => void;
    onCitations: (items: Citation[]) => void;
    onDone: () => void;
    onError: (code: string, message: string) => void;
  },
  lang: "en" | "it",
): Promise<void> {
  const { onToken, onCitations, onDone, onError } = handlers;
  let response: Response;
  try {
    response = await fetch(`/api/conversations/${id}/messages`, {
      method: "POST",
      headers: {
        ...(await authHeader()),
        "Content-Type": "application/json",
        "Accept-Language": lang,
      },
      body: JSON.stringify({ content }),
    });
  } catch (err) {
    if (err instanceof Error && err.message === "Sign in again.") throw err;
    onError("upstream", "API unreachable");
    return;
  }

  if (!response.ok || !response.body) {
    onError("upstream", "API unreachable");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  let eventName: string | null = null;
  let dataLine: string | null = null;
  let stopped = false;

  function dispatch(name: string, raw: string) {
    let payload: unknown;
    try {
      payload = JSON.parse(raw);
    } catch {
      stopped = true;
      onError("upstream", "API unreachable");
      return;
    }
    const record =
      payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
    if (name === "token") {
      onToken(typeof record.text === "string" ? record.text : "");
      return;
    }
    if (name === "citations") {
      onCitations(Array.isArray(record.citations) ? (record.citations as Citation[]) : []);
      return;
    }
    if (name === "done") {
      onDone();
      return;
    }
    if (name === "error") {
      onError(
        typeof record.code === "string" ? record.code : "upstream",
        typeof record.message === "string" ? record.message : "API unreachable",
      );
    }
  }

  function emitIfReady() {
    if (stopped || eventName === null || dataLine === null) return;
    const name = eventName;
    const raw = dataLine;
    eventName = null;
    dataLine = null;
    dispatch(name, raw);
  }

  function handleLine(line: string) {
    if (stopped) return;
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      emitIfReady();
      return;
    }
    if (line.startsWith("data:")) {
      dataLine = line.slice("data:".length).trim();
      emitIfReady();
    }
  }

  function pushText(text: string) {
    pending += text;
    const lines = pending.split("\n");
    pending = lines.pop() ?? "";
    for (const line of lines) {
      if (stopped) return;
      handleLine(line.endsWith("\r") ? line.slice(0, -1) : line);
    }
  }

  try {
    while (!stopped) {
      const { done, value } = await reader.read();
      if (done) break;
      pushText(decoder.decode(value, { stream: true }));
    }
    if (!stopped) {
      pushText(decoder.decode());
      if (!stopped && pending) {
        handleLine(pending.endsWith("\r") ? pending.slice(0, -1) : pending);
        pending = "";
      }
    }
  } catch {
    if (!stopped) onError("upstream", "API unreachable");
  } finally {
    if (stopped) {
      try {
        await reader.cancel();
      } catch {
        /* reader already closed */
      }
    }
  }
}