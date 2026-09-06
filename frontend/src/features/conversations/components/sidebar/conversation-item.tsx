import { Trash2 } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/cn";
import type { ConversationSummary } from "@/types/conversation";

interface ConversationItemProps {
  conversation: ConversationSummary;
  onDelete: (id: string) => void;
}

/** One row in the sidebar list: a link to the conversation with a hover-to-delete button. */
export function ConversationItem({ conversation, onDelete }: ConversationItemProps) {
  return (
    <div className="group relative">
      <NavLink
        to={`/c/${conversation.id}`}
        className={({ isActive }) =>
          cn(
            "block truncate rounded-md py-2 pr-8 pl-3 text-sm transition-colors",
            isActive
              ? "bg-accent/60 text-foreground"
              : "text-muted-foreground hover:bg-accent/40 hover:text-foreground",
          )
        }
      >
        {conversation.title}
      </NavLink>

      <button
        type="button"
        aria-label={`Delete ${conversation.title}`}
        onClick={() => onDelete(conversation.id)}
        className="text-muted-foreground hover:text-foreground absolute top-1/2 right-1 hidden -translate-y-1/2 rounded p-1.5 group-hover:block"
      >
        <Trash2 className="size-3.5" />
      </button>
    </div>
  );
}
