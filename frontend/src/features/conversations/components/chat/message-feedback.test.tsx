import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as feedbackApi from "@/features/conversations/api/feedback";
import { MessageFeedback } from "@/features/conversations/components/chat/message-feedback";

describe("MessageFeedback", () => {
  it("sends the rating and marks the button pressed", async () => {
    const spy = vi.spyOn(feedbackApi, "submitFeedback").mockResolvedValue(undefined);

    render(<MessageFeedback traceId="trace-1" />);
    await userEvent.click(screen.getByRole("button", { name: "Not helpful" }));

    expect(spy).toHaveBeenCalledWith("trace-1", false);
    expect(screen.getByRole("button", { name: "Not helpful" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
