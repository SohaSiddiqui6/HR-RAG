import { useState } from "react";

import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationItem } from "@/features/conversations/components/sidebar/conversation-item";
import { useConversations } from "@/features/conversations/hooks/use-conversations";

/** Sidebar "Recent chats" list. */
export function ConversationList() {
  const { conversations, isLoading, remove } = useConversations();
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const pendingDelete = conversations.find((c) => c.id === pendingDeleteId);

  function confirmDelete() {
    if (pendingDeleteId) remove(pendingDeleteId);
    setPendingDeleteId(null);
  }

  if (isLoading) {
    return (
      <div className="mt-3 space-y-1 px-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <p className="text-muted-foreground mt-3 px-3 text-sm">
        Your conversations will appear here.
      </p>
    );
  }

  return (
    <div className="mt-2 space-y-0.5">
      {conversations.map((conversation) => (
        <ConversationItem
          key={conversation.id}
          conversation={conversation}
          onDelete={setPendingDeleteId}
        />
      ))}

      <ConfirmDialog
        open={pendingDelete !== undefined}
        title="Delete conversation?"
        description={
          pendingDelete && `"${pendingDelete.title}" will be permanently removed.`
        }
        confirmLabel="Delete"
        onConfirm={confirmDelete}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}
