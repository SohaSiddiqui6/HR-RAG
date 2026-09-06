import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ConversationList } from "@/features/conversations/components/sidebar/conversation-list";
import { renderWithProviders } from "@/test/render";

async function seedConversation(question: string) {
  const { id } = await (await fetch("/api/conversations", { method: "POST" })).json();
  await fetch(`/api/conversations/${id}/messages/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return { id } as { id: string };
}

function renderList(path = "/") {
  return renderWithProviders(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<ConversationList />} />
        <Route path="/c/:conversationId" element={<ConversationList />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ConversationList", () => {
  it("renders a row per conversation", async () => {
    await seedConversation("PTO carryover");

    renderList();

    expect(
      await screen.findByRole("link", { name: "PTO carryover" }),
    ).toBeInTheDocument();
  });

  it("marks the open conversation as active", async () => {
    const { id } = await seedConversation("Parental leave");

    renderList(`/c/${id}`);

    expect(await screen.findByRole("link", { name: "Parental leave" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("navigates to a conversation when its row is clicked", async () => {
    await seedConversation("Remote work");

    renderList();
    await userEvent.click(await screen.findByRole("link", { name: "Remote work" }));

    // The list re-renders at /c/:id, so the clicked row is now the active one.
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "Remote work" })).toHaveAttribute(
        "aria-current",
        "page",
      ),
    );
  });

  it("deletes a conversation after confirming in the dialog", async () => {
    await seedConversation("Expense policy");

    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete Expense policy" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(
        screen.queryByRole("link", { name: "Expense policy" }),
      ).not.toBeInTheDocument(),
    );
  });

  it("keeps the conversation when the dialog is cancelled", async () => {
    await seedConversation("Dress code");

    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete Dress code" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByRole("link", { name: "Dress code" })).toBeInTheDocument();
  });
});
