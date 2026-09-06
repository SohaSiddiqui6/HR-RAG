import { Sparkles } from "lucide-react";
import { useParams } from "react-router-dom";

import { EmptyState } from "@/components/common/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatComposer } from "@/features/conversations/components/chat/chat-composer";
import { MessageList } from "@/features/conversations/components/chat/message-list";
import { useConversation } from "@/features/conversations/hooks/use-conversation";
import type { Message } from "@/types/conversation";

function bubble(id: string, role: Message["role"], content: string): Message {
  return { id, role, content, createdAt: "" };
}

/** Centre pane: header · conversation (or welcome) · composer. */
export function ChatView() {
  const { conversationId } = useParams();
  const { messages, pendingText, streamingText, send, isPending, isLoading } =
    useConversation(conversationId);

  const displayed = [...messages];
  if (pendingText) displayed.push(bubble("pending-user", "user", pendingText));
  if (streamingText !== null) {
    displayed.push(bubble("streaming", "assistant", streamingText));
  }

  const showWelcome = !isLoading && displayed.length === 0 && !isPending;
  const showTyping = isPending && streamingText === null;

  return (
    <div className="flex h-full flex-col">
      <header className="border-border text-muted-foreground flex h-14 items-center border-b px-6 text-sm">
        Ask HR
      </header>

      {isLoading ? (
        <div className="mx-auto w-full max-w-3xl space-y-6 px-6 py-8">
          <Skeleton className="ml-auto h-10 w-48" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : showWelcome ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <EmptyState
            icon={Sparkles}
            title="How can I help with HR?"
            description="Ask about policies, benefits, time off, or anything workplace-related."
          />
        </div>
      ) : (
        <MessageList messages={displayed} pending={showTyping} />
      )}

      <ChatComposer onSend={send} disabled={isPending} />
    </div>
  );
}
