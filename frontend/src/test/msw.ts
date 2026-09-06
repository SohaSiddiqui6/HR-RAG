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
  http.get("*/api/conversations", () =>
    HttpResponse.json(
      [...store.values()].map((c) => ({
        id: c.id,
        title: c.title,
        updated_at: c.updated_at,
      })),
    ),
  ),

  http.post("*/api/conversations", async ({ request }) => {
    const { question } = (await request.json().catch(() => ({}))) as {
      question?: string;
    };
    const c = conversation(crypto.randomUUID());
    if (question) {
      c.title = question.slice(0, 60);
      c.messages.push(
        message("user", question),
        message("assistant", `You asked: ${question}`),
      );
    }
    store.set(c.id, c);
    return HttpResponse.json(c);
  }),

  http.get("*/api/conversations/:id", ({ params }) => {
    const c = store.get(params.id as string);
    return c
      ? HttpResponse.json(c)
      : HttpResponse.json({ error: "Conversation not found" }, { status: 404 });
  }),

  http.post("*/api/conversations/:id/messages", async ({ params, request }) => {
    const c = store.get(params.id as string);
    if (!c)
      return HttpResponse.json({ error: "Conversation not found" }, { status: 404 });
    const { question } = (await request.json()) as { question: string };
    const user = message("user", question);
    const assistant = message("assistant", `You asked: ${question}`);
    c.messages.push(user, assistant);
    return HttpResponse.json({ user_message: user, assistant_message: assistant });
  }),

  http.delete("*/api/conversations/:id", ({ params }) => {
    store.delete(params.id as string);
    return new HttpResponse(null, { status: 204 });
  }),
];

export const server = setupServer(...handlers);
