import { Sparkles } from "lucide-react";

import { Markdown } from "@/components/common/markdown";
import type { Message } from "@/features/chat/types";

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-user-bubble text-user-bubble-foreground max-w-[75%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="bg-primary/15 text-primary mt-1 flex size-7 shrink-0 items-center justify-center rounded-lg">
        <Sparkles className="size-3.5" />
      </div>
      <div className="border-border bg-card min-w-0 flex-1 rounded-xl border p-4">
        <Markdown>{message.content}</Markdown>
      </div>
    </div>
  );
}
