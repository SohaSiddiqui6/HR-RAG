import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ChatView } from "@/features/conversations/components/chat/chat-view";
import { server } from "@/test/msw";
import { renderWithProviders } from "@/test/render";

function renderChat(path = "/") {
  return renderWithProviders(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<ChatView />} />
        <Route path="/c/:conversationId" element={<ChatView />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function ask(question: string) {
  await userEvent.type(
    screen.getByRole("textbox", { name: "Message" }),
    `${question}{Enter}`,
  );
}

async function seedConversation(question: string): Promise<string> {
  const { id } = await (await fetch("/api/conversations", { method: "POST" })).json();
  await fetch(`/api/conversations/${id}/messages/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return id;
}

describe("ChatView", () => {
  it("creates a conversation on the first question and streams the answer", async () => {
    renderChat("/");
    expect(
      screen.getByRole("heading", { name: "How can I help with HR?" }),
    ).toBeInTheDocument();

    await ask("What is the PTO carryover limit?");

    expect(
      await screen.findByText("You asked: What is the PTO carryover limit?"),
    ).toBeInTheDocument();
    expect(screen.getByText("What is the PTO carryover limit?")).toBeInTheDocument();
  });

  it("loads an existing conversation by id", async () => {
    const id = await seedConversation("existing question");

    renderChat(`/c/${id}`);

    expect(await screen.findByText("existing question")).toBeInTheDocument();
    expect(screen.getByText("You asked: existing question")).toBeInTheDocument();
  });

  it("shows an inline error when the stream fails", async () => {
    server.use(
      http.post("*/api/conversations/:id/messages/stream", () =>
        HttpResponse.json({ error: "Question is empty." }, { status: 400 }),
      ),
    );
    renderChat("/");

    await ask("hi");

    expect(await screen.findByText("Question is empty.")).toBeInTheDocument();
  });
});
