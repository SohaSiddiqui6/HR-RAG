import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageBubble } from "@/features/chat/components/message-bubble";
import type { Message } from "@/features/chat/types";

const base = { id: "1", createdAt: "2026-01-01T00:00:00.000Z" };

describe("MessageBubble", () => {
  it("renders a user message as plain text", () => {
    const message: Message = { ...base, role: "user", content: "- not a list" };
    render(<MessageBubble message={message} />);

    expect(screen.getByText("- not a list")).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("renders an assistant message as markdown", () => {
    const message: Message = { ...base, role: "assistant", content: "- first\n- second" };
    render(<MessageBubble message={message} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders a failed assistant message as an error, not markdown", () => {
    const message: Message = {
      ...base,
      role: "assistant",
      content: "Something went wrong.",
      failed: true,
    };
    render(<MessageBubble message={message} />);

    expect(screen.getByText("Something went wrong.")).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });
});
