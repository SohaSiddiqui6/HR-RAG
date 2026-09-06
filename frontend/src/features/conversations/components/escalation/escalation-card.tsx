import { LifeBuoy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EscalationDialog } from "@/features/conversations/components/escalation/escalation-dialog";
import type { Message } from "@/types/conversation";

/** Shown under a `needs_human` answer: offer a handoff, or confirm one was sent. */
export function EscalationCard({ message }: { message: Message }) {
  const [open, setOpen] = useState(false);
  const { escalation } = message;

  return (
    <div className="border-border bg-panel mt-3 rounded-xl border p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <LifeBuoy className="text-muted-foreground size-4" />
        {escalation ? "Sent to HR" : "Can't find what you need?"}
      </div>

      {escalation ? (
        <p className="text-muted-foreground mt-1 text-sm">
          The HR team has your request
          {escalation.reference ? ` (${escalation.reference})` : ""} and will follow up.
        </p>
      ) : (
        <>
          <p className="text-muted-foreground mt-1 text-sm">
            Send this question to the HR team and someone will follow up.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => setOpen(true)}
          >
            Open an HR request
          </Button>
          <EscalationDialog
            messageId={message.id}
            open={open}
            onClose={() => setOpen(false)}
          />
        </>
      )}
    </div>
  );
}
