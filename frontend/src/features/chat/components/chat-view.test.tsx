import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ChatView } from "@/features/chat/components/chat-view";

describe("ChatView", () => {
  it("shows the welcome state, then the exchange after sending", async () => {
    render(<ChatView />);
    expect(
      screen.getByRole("heading", { name: "How can I help with HR?" }),
    ).toBeInTheDocument();

    await userEvent.type(
      screen.getByRole("textbox", { name: "Message" }),
      "What is the parental leave policy?{Enter}",
    );

    expect(
      screen.queryByRole("heading", { name: "How can I help with HR?" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("What is the parental leave policy?")).toBeInTheDocument();
    expect(
      screen.getByText("Available to all full-time employees after 90 days of service"),
    ).toBeInTheDocument();
  });
});
