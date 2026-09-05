import { Sparkles } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ChatComposer } from "@/features/chat/components/chat-composer";
import { MessageList } from "@/features/chat/components/message-list";
import { CANNED_REPLY } from "@/features/chat/mock";
import type { Message } from "@/features/chat/types";

function createMessage(role: Message["role"], content: string): Message {
  return { id: crypto.randomUUID(), role, content, createdAt: new Date().toISOString() };
}

/**
 * Centre pane. Step 2 drives the conversation from local state with a canned
 * reply; Step 3 replaces the reply with the `POST /api/ask` mutation.
 */
export function ChatView() {
  const [messages, setMessages] = useState<Message[]>([]);

  function handleSend(text: string) {
    setMessages((prev) => [
      ...prev,
      createMessage("user", text),
      createMessage("assistant", CANNED_REPLY),
    ]);
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-border text-muted-foreground flex h-14 items-center border-b px-6 text-sm">
        Ask HR
      </header>

      {messages.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <EmptyState
            icon={Sparkles}
            title="How can I help with HR?"
            description="Ask about policies, benefits, time off, or anything workplace-related."
          />
        </div>
      ) : (
        <MessageList messages={messages} />
      )}

      <ChatComposer onSend={handleSend} />
    </div>
  );
}
