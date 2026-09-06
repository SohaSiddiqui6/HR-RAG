import { screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppLayout } from "@/app/layout/app-layout";
import { ChatView } from "@/features/conversations/components/chat/chat-view";
import { renderWithProviders } from "@/test/render";

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <ChatView /> },
          { path: "/c/:conversationId", element: <ChatView /> },
        ],
      },
    ],
    { initialEntries: [path] },
  );
  return renderWithProviders(<RouterProvider router={router} />);
}

describe("AppLayout", () => {
  it("renders the three panes and the welcome state at /", () => {
    renderAt("/");
    expect(screen.getByText("Peoplewise")).toBeInTheDocument();
    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "How can I help with HR?" }),
    ).toBeInTheDocument();
  });

  it("renders the shell for a conversation deep-link", async () => {
    renderAt("/c/abc123");
    // The chat pane loads (or 404s) — the layout still frames it.
    expect(screen.getByText("Peoplewise")).toBeInTheDocument();
    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "How can I help with HR?" }),
    ).toBeInTheDocument();
  });
});
