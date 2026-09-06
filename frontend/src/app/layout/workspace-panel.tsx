import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { getConversation } from "@/features/conversations/api/conversations";
import { conversationKeys } from "@/features/conversations/api/keys";
import { PolicyCoverageCard } from "@/features/workspace/components/policy-coverage-card";
import type { Message } from "@/types/conversation";

/** Distinct policy documents cited across a conversation's answers, in first-seen order. */
function citedDocuments(messages: Message[]): string[] {
  const seen = new Set<string>();
  for (const message of messages) {
    for (const source of message.sources ?? []) seen.add(source.document);
  }
  return [...seen];
}

/** Right pane: policy coverage — the whole index, or just what the open chat used. */
export function WorkspacePanel() {
  const { conversationId } = useParams();
  const { data } = useQuery({
    queryKey: conversationKeys.detail(conversationId ?? ""),
    queryFn: () => getConversation(conversationId!),
    enabled: Boolean(conversationId),
  });

  return (
    <aside
      aria-label="Workspace"
      className="border-border bg-panel flex h-full flex-col gap-6 overflow-y-auto border-l p-5"
    >
      <div>
        <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
          Workspace
        </div>
        <div className="mt-1 text-lg font-semibold">HR help center</div>
      </div>

      <PolicyCoverageCard
        citedDocuments={data ? citedDocuments(data.messages) : undefined}
      />
    </aside>
  );
}
