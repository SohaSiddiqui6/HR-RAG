import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppLayout } from "@/app/layout/app-layout";
import { ChatView } from "@/features/chat/components/chat-view";

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
  return render(<RouterProvider router={router} />);
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

  it("renders for a conversation deep-link", () => {
    renderAt("/c/abc123");
    expect(
      screen.getByRole("heading", { name: "How can I help with HR?" }),
    ).toBeInTheDocument();
  });
});
