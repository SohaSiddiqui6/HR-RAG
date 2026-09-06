import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ChatView } from "@/features/conversations/components/chat/chat-view";
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

describe("escalation", () => {
  it("offers a handoff only when the answer needs a human", async () => {
    renderChat("/");
    await ask("What is the PTO carryover limit?");

    expect(await screen.findByText(/You asked:/)).toBeInTheDocument();
    expect(screen.queryByText("Can't find what you need?")).not.toBeInTheDocument();
  });

  it("auto-fills the request and sends it to HR", async () => {
    renderChat("/");
    await ask("Do we reimburse a standing desk?");

    await userEvent.click(
      await screen.findByRole("button", { name: "Open an HR request" }),
    );

    const subject = screen.getByLabelText("Subject") as HTMLInputElement;
    const details = screen.getByLabelText("Details") as HTMLTextAreaElement;
    expect(subject.value).toBe("Do we reimburse a standing desk?");
    expect(details.value).toContain("standing desk");

    await userEvent.click(screen.getByRole("button", { name: "Send to HR" }));

    expect(await screen.findByText("Sent to HR")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Open an HR request" }),
    ).not.toBeInTheDocument();
  });
});
