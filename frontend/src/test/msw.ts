import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

/** Default happy-path handler. Tests override per-case with `server.use(...)`. */
export const handlers = [
  http.post("*/api/ask", async ({ request }) => {
    const { question } = (await request.json()) as { question: string };
    return HttpResponse.json({
      answer: `You asked: ${question}`,
      sources: [
        { source: "pto-and-leave-policy.pdf", page_no: 1, headings: "2.2 PTO Carryover" },
      ],
    });
  }),
];

export const server = setupServer(...handlers);
