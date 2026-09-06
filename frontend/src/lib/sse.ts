/**
 * Read a Server-Sent Events response body, invoking `onEvent` with each parsed
 * `data:` payload. Events are separated by a blank line; only `data:` lines are
 * used (this API doesn't send event names or ids).
 */
export async function readSSE(
  response: Response,
  onEvent: (data: unknown) => void,
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((l) => l.startsWith("data:"));
      if (line) onEvent(JSON.parse(line.slice(5).trim()));
    }
  }
}
