import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "@/features/conversations/components/chat/chat-composer";

describe("ChatComposer", () => {
  it("sends on Enter and clears the field", async () => {
    const onSend = vi.fn();
    render(<ChatComposer onSend={onSend} />);
    const field = screen.getByRole("textbox", { name: "Message" });

    await userEvent.type(field, "how much PTO?{Enter}");

    expect(onSend).toHaveBeenCalledExactlyOnceWith("how much PTO?");
    expect(field).toHaveValue("");
  });

  it("inserts a newline on Shift+Enter without sending", async () => {
    const onSend = vi.fn();
    render(<ChatComposer onSend={onSend} />);
    const field = screen.getByRole("textbox", { name: "Message" });

    await userEvent.type(field, "line one{Shift>}{Enter}{/Shift}line two");

    expect(onSend).not.toHaveBeenCalled();
    expect(field).toHaveValue("line one\nline two");
  });

  it("disables the send button when empty", () => {
    render(<ChatComposer onSend={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("cannot send while an answer is streaming", async () => {
    const onSend = vi.fn();
    render(<ChatComposer onSend={onSend} disabled />);
    const field = screen.getByRole("textbox", { name: "Message" });

    await userEvent.type(field, "another question{Enter}");

    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(field).toHaveAttribute("placeholder", "Answering…");
  });
});
