import { MessageBubble } from "@/features/chat/components/message-bubble";
import { useAutoScroll } from "@/features/chat/hooks/use-auto-scroll";
import type { Message } from "@/features/chat/types";

export function MessageList({ messages }: { messages: Message[] }) {
  const scrollRef = useAutoScroll<HTMLDivElement>(messages.length);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
}
