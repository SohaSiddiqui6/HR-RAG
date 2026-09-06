import { Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { ChatComposer } from "@/features/chat/components/chat-composer";
import { MessageList } from "@/features/chat/components/message-list";
import { useConversation } from "@/features/chat/hooks/use-conversation";

/** Centre pane: header · conversation (or welcome) · composer. */
export function ChatView() {
  const { messages, send, isPending } = useConversation();
  const showWelcome = messages.length === 0 && !isPending;

  return (
    <div className="flex h-full flex-col">
      <header className="border-border text-muted-foreground flex h-14 items-center border-b px-6 text-sm">
        Ask HR
      </header>

      {showWelcome ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <EmptyState
            icon={Sparkles}
            title="How can I help with HR?"
            description="Ask about policies, benefits, time off, or anything workplace-related."
          />
        </div>
      ) : (
        <MessageList messages={messages} pending={isPending} />
      )}

      <ChatComposer onSend={send} disabled={isPending} />
    </div>
  );
}
