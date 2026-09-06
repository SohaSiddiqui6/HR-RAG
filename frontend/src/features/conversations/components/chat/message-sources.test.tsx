import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { MessageSources } from "@/features/conversations/components/chat/message-sources";
import type { Source } from "@/types/conversation";

describe("MessageSources", () => {
  it("groups repeated chunks by document and lists their pages", async () => {
    const sources: Source[] = [
      { document: "pto-and-leave-policy.pdf", page: 4, heading: "2.2 Carryover" },
      { document: "pto-and-leave-policy.pdf", page: 2 },
      { document: "code-of-conduct.pdf", page: 1 },
    ];
    render(<MessageSources sources={sources} />);

    expect(screen.getByText("Sources · 2")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Sources · 2"));
    expect(screen.getByText("pto-and-leave-policy")).toBeInTheDocument();
    expect(screen.getByText("· p. 2, 4")).toBeInTheDocument();
    expect(screen.getByText("code-of-conduct")).toBeInTheDocument();
  });

  it("renders nothing when there are no sources", () => {
    const { container } = render(<MessageSources sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
