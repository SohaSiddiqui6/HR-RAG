import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { ChatView } from "@/features/chat/components/chat-view";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/msw";

async function ask(question: string) {
  await userEvent.type(
    screen.getByRole("textbox", { name: "Message" }),
    `${question}{Enter}`,
  );
}

describe("ChatView", () => {
  it("sends a question and renders the answer", async () => {
    renderWithProviders(<ChatView />);
    expect(
      screen.getByRole("heading", { name: "How can I help with HR?" }),
    ).toBeInTheDocument();

    await ask("What is the PTO carryover limit?");

    expect(screen.getByText("What is the PTO carryover limit?")).toBeInTheDocument();
    expect(
      await screen.findByText("You asked: What is the PTO carryover limit?"),
    ).toBeInTheDocument();
  });

  it("shows an inline error when the request fails", async () => {
    server.use(
      http.post("*/api/ask", () =>
        HttpResponse.json({ error: "Question is empty." }, { status: 400 }),
      ),
    );
    renderWithProviders(<ChatView />);

    await ask("hi");

    expect(await screen.findByText("Question is empty.")).toBeInTheDocument();
  });

  it("disables the composer and shows a typing indicator while pending", async () => {
    let resolve: (() => void) | undefined;
    server.use(
      http.post("*/api/ask", async () => {
        await new Promise<void>((r) => {
          resolve = r;
        });
        return HttpResponse.json({ answer: "done", sources: [] });
      }),
    );
    renderWithProviders(<ChatView />);

    await ask("slow one");

    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(screen.getByLabelText("Assistant is typing")).toBeInTheDocument();

    resolve?.();
    expect(await screen.findByText("done")).toBeInTheDocument();
  });
});
