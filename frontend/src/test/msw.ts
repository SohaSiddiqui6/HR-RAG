import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

const source = {
  source: "pto-and-leave-policy.pdf",
  page_no: 1,
  headings: "2.2 PTO Carryover",
};

function message(
  role: "user" | "assistant",
  content: string,
  outcome: "answered" | "needs_human" | "out_of_scope" = "answered",
) {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    sources: role === "assistant" && outcome === "answered" ? [source] : [],
    outcome,
    escalation: null as {
      channel: string;
      reference: string | null;
      url: string | null;
    } | null,
    trace_id: role === "assistant" ? crypto.randomUUID() : null,
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
    // "standing desk" is the test's stand-in for an HR question the docs don't cover.
    const needsHuman = /standing desk/i.test(question);
    const answer = needsHuman
      ? "I couldn't find this in the current HR policies."
      : `You asked: ${question}`;
    c.messages.push(
      message("user", question),
      message("assistant", answer, needsHuman ? "needs_human" : "answered"),
    );
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

  http.post("*/api/conversations/:id/escalation", async ({ params, request }) => {
    const c = store.get(params.id as string);
    const { message_id } = (await request.json()) as { message_id: string };
    const target = c?.messages.find((m) => m.id === message_id);
    if (!c || !target)
      return HttpResponse.json({ error: "Conversation not found" }, { status: 404 });
    if (target.outcome !== "needs_human")
      return HttpResponse.json({ error: "can't be escalated" }, { status: 409 });

    target.escalation ??= { channel: "log", reference: null, url: null };
    return HttpResponse.json(target.escalation);
  }),

  http.post("*/api/feedback", () => new HttpResponse(null, { status: 204 })),

  http.delete("*/api/conversations/:id", ({ params }) => {
    store.delete(params.id as string);
    return new HttpResponse(null, { status: 204 });
  }),
];

export const server = setupServer(...handlers);
