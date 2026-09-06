import { MessageBubble } from "@/features/chat/components/message-bubble";
import { TypingIndicator } from "@/features/chat/components/typing-indicator";
import { useAutoScroll } from "@/features/chat/hooks/use-auto-scroll";
import type { Message } from "@/features/chat/types";

interface MessageListProps {
  messages: Message[];
  pending?: boolean;
}

export function MessageList({ messages, pending = false }: MessageListProps) {
  const scrollRef = useAutoScroll<HTMLDivElement>(messages.length + (pending ? 1 : 0));

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {pending && <TypingIndicator />}
      </div>
    </div>
  );
}
