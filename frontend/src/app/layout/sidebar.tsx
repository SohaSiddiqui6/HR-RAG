import { BookOpen, Inbox, MessageSquare, Plus } from "lucide-react";

import { Brand } from "@/components/common/brand";
import { Button } from "@/components/ui/button";

// Placeholder nav — wired up in later steps.
const NAV_ITEMS = [
  { icon: MessageSquare, label: "Ask HR", active: true },
  { icon: Inbox, label: "My requests" },
  { icon: BookOpen, label: "Policy library" },
];

/** Left pane: brand, new-conversation action, nav, recent chats. */
export function Sidebar() {
  return (
    <aside className="border-border bg-panel flex h-full flex-col gap-4 border-r p-4">
      <Brand />

      <Button className="w-full justify-start" disabled>
        <Plus /> New conversation
      </Button>

      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            type="button"
            className={
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors " +
              (active
                ? "bg-accent/60 text-foreground"
                : "text-muted-foreground hover:bg-accent/40 hover:text-foreground")
            }
          >
            <Icon className="size-4" />
            {label}
          </button>
        ))}
      </nav>

      <div className="mt-2 flex-1 overflow-y-auto">
        <div className="text-muted-foreground px-3 text-xs font-medium tracking-wide uppercase">
          Recent chats
        </div>
        <p className="text-muted-foreground mt-3 px-3 text-sm">
          Your conversations will appear here.
        </p>
      </div>
    </aside>
  );
}
