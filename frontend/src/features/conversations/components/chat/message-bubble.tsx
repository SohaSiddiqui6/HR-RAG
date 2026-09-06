import { Sparkles, TriangleAlert } from "lucide-react";

import { Markdown } from "@/components/common/markdown";
import { MessageSources } from "@/features/conversations/components/chat/message-sources";
import { EscalationCard } from "@/features/conversations/components/escalation/escalation-card";
import type { Message } from "@/types/conversation";

function AssistantAvatar({ error = false }: { error?: boolean }) {
  const Icon = error ? TriangleAlert : Sparkles;
  return (
    <div
      className={
        "mt-1 flex size-7 shrink-0 items-center justify-center rounded-lg " +
        (error ? "bg-destructive/15 text-destructive" : "bg-primary/15 text-primary")
      }
    >
      <Icon className="size-3.5" />
    </div>
  );
}

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

  if (message.failed) {
    return (
      <div className="flex gap-3">
        <AssistantAvatar error />
        <div className="border-destructive/40 bg-destructive/10 text-destructive-foreground min-w-0 flex-1 rounded-xl border p-4 text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <AssistantAvatar />
      <div className="min-w-0 flex-1">
        <div className="border-border bg-card rounded-xl border p-4">
          <Markdown>{message.content}</Markdown>
          {message.sources && <MessageSources sources={message.sources} />}
        </div>
        {message.outcome === "needs_human" && <EscalationCard message={message} />}
      </div>
    </div>
  );
}
