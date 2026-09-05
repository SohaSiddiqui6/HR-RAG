import { Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";

/**
 * Centre pane. Step 1 renders only the welcome state; the message list and
 * composer arrive in Step 2.
 */
export function ChatView() {
  return (
    <div className="flex h-full flex-col">
      <header className="border-border text-muted-foreground flex h-14 items-center border-b px-6 text-sm">
        Ask HR
      </header>
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState
          icon={Sparkles}
          title="How can I help with HR?"
          description="Ask about policies, benefits, time off, or anything workplace-related."
        />
      </div>
    </div>
  );
}
