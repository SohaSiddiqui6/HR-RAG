import { Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { Brand } from "@/components/common/brand";
import { Button } from "@/components/ui/button";
import { ConversationList } from "@/features/conversations/components/conversation-list";

/** Left pane: brand, new-conversation action, recent chats. */
export function Sidebar() {
  return (
    <aside className="border-border bg-panel flex h-full flex-col gap-4 border-r p-4">
      <Brand />

      <Button asChild className="w-full justify-start">
        <Link to="/">
          <Plus /> New conversation
        </Link>
      </Button>

      <div className="mt-2 flex-1 overflow-y-auto">
        <div className="text-muted-foreground px-3 text-xs font-medium tracking-wide uppercase">
          Recent chats
        </div>
        <ConversationList />
      </div>
    </aside>
  );
}
