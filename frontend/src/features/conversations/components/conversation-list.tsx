import { Skeleton } from "@/components/ui/skeleton";
import { ConversationItem } from "@/features/conversations/components/conversation-item";
import { useConversations } from "@/features/conversations/hooks/use-conversations";

/** Sidebar "Recent chats" list. */
export function ConversationList() {
  const { conversations, isLoading, remove } = useConversations();

  function handleDelete(id: string) {
    const target = conversations.find((c) => c.id === id);
    if (window.confirm(`Delete "${target?.title}"?`)) remove(id);
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
          onDelete={handleDelete}
        />
      ))}
    </div>
  );
}
