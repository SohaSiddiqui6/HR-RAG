import { config } from "@/lib/config";
import { readSSE } from "@/lib/sse";
import { ApiError } from "@/types/api";

interface StreamEvent {
  type: "token" | "done" | "error";
  text?: string;
  error?: string;
}

/**
 * POST a question and stream the grounded answer back as Server-Sent Events.
 * `onToken` fires per chunk; the promise resolves once the server has persisted
 * the answer (`done`), and rejects on an `error` event or a guardrail 400.
 */
export async function streamMessage(
  conversationId: string,
  question: string,
  onToken: (text: string) => void,
): Promise<void> {
  const response = await fetch(
    `${config.apiBaseUrl}/conversations/${conversationId}/messages/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
  );

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String((payload as { error: unknown }).error)
        : `Request failed (${response.status})`;
    throw new ApiError(response.status, message, payload);
  }

  let failure: string | undefined;
  await readSSE(response, (data) => {
    const event = data as StreamEvent;
    if (event.type === "token") onToken(event.text ?? "");
    else if (event.type === "error") failure = event.error;
  });

  if (failure) throw new ApiError(0, failure);
}
