import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

const source = {
  source: "pto-and-leave-policy.pdf",
  page_no: 1,
  headings: "2.2 PTO Carryover",
};

function message(role: "user" | "assistant", content: string) {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    sources: role === "assistant" ? [source] : [],
    created_at: new Date().toISOString(),
  };
}

/**
 * A tiny in-memory conversation store so tests exercise the real request flow.
 * Reset in `test/setup.ts` between tests.
 */
const store = new Map<string, ReturnType<typeof conversation>>();

function conversation(id: string, title = "New conversation") {
  const now = new Date().toISOString();
  return {
    id,
    title,
    created_at: now,
    updated_at: now,
    messages: [] as ReturnType<typeof message>[],
  };
}

export function resetStore() {
  store.clear();
}

export const handlers = [
  http.get("*/api/workspace", () =>
    HttpResponse.json({
      documents: ["pto-and-leave-policy.pdf", "code-of-conduct.pdf"],
      document_count: 2,
      chunk_count: 137,
    }),
  ),

  http.get("*/api/conversations", () =>
    HttpResponse.json(
      [...store.values()].map((c) => ({
        id: c.id,
        title: c.title,
        updated_at: c.updated_at,
      })),
    ),
  ),

  http.post("*/api/conversations", () => {
    const c = conversation(crypto.randomUUID());
    store.set(c.id, c);
    return HttpResponse.json(c);
  }),

  http.get("*/api/conversations/:id", ({ params }) => {
    const c = store.get(params.id as string);
    return c
      ? HttpResponse.json(c)
      : HttpResponse.json({ error: "Conversation not found" }, { status: 404 });
  }),

  http.post("*/api/conversations/:id/messages/stream", async ({ params, request }) => {
    const c = store.get(params.id as string);
    if (!c)
      return HttpResponse.json({ error: "Conversation not found" }, { status: 404 });

    const { question } = (await request.json()) as { question: string };
    const answer = `You asked: ${question}`;
    c.messages.push(message("user", question), message("assistant", answer));
    if (c.title === "New conversation") c.title = question.slice(0, 60);
    c.updated_at = new Date().toISOString();

    const encoder = new TextEncoder();
    const sse = (data: unknown) => encoder.encode(`data: ${JSON.stringify(data)}\n\n`);
    const body = new ReadableStream({
      start(controller) {
        for (const word of answer.split(" ")) {
          controller.enqueue(sse({ type: "token", text: `${word} ` }));
        }
        controller.enqueue(sse({ type: "done" }));
        controller.close();
      },
    });
    return new HttpResponse(body, {
      headers: { "Content-Type": "text/event-stream" },
    });
  }),

  http.delete("*/api/conversations/:id", ({ params }) => {
    store.delete(params.id as string);
    return new HttpResponse(null, { status: 204 });
  }),
];

export const server = setupServer(...handlers);
