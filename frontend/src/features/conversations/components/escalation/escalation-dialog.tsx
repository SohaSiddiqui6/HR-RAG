import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { getConversation } from "@/features/conversations/api/conversations";
import { conversationKeys } from "@/features/conversations/api/keys";
import { buildDraft } from "@/features/conversations/components/escalation/draft";
import { useEscalation } from "@/features/conversations/hooks/use-escalation";

interface EscalationDialogProps {
  messageId: string;
  open: boolean;
  onClose: () => void;
}

/** Review + edit the auto-filled HR request, then send it. Native `<dialog>`. */
export function EscalationDialog({ messageId, open, onClose }: EscalationDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const { conversationId = "" } = useParams();

  const { data: conversation } = useQuery({
    queryKey: conversationKeys.detail(conversationId),
    queryFn: () => getConversation(conversationId),
    enabled: Boolean(conversationId),
  });
  const escalation = useEscalation(conversationId);

  // The conversation is already cached (the card only renders once it's loaded),
  // so the draft is ready on first render.
  const [form, setForm] = useState(() => buildDraft(conversation, messageId));

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  function send() {
    escalation.mutate(
      { messageId, subject: form.subject.trim(), body: form.body.trim() },
      { onSuccess: onClose },
    );
  }

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className="border-border bg-card text-card-foreground m-auto w-[calc(100%-2rem)] max-w-md rounded-xl border p-5 backdrop:bg-black/50"
    >
      <h2 className="font-medium">Open an HR request</h2>
      <p className="text-muted-foreground mt-1 text-sm">
        This goes to the HR team in Slack.
      </p>

      <label
        htmlFor="escalation-subject"
        className="text-muted-foreground mt-4 block text-xs font-medium tracking-wide uppercase"
      >
        Subject
      </label>
      <input
        id="escalation-subject"
        value={form.subject}
        onChange={(e) => setForm({ ...form, subject: e.target.value })}
        className="border-input focus-visible:ring-ring mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm focus-visible:ring-2 focus-visible:outline-none"
      />

      <label
        htmlFor="escalation-details"
        className="text-muted-foreground mt-3 block text-xs font-medium tracking-wide uppercase"
      >
        Details
      </label>
      <Textarea
        id="escalation-details"
        value={form.body}
        onChange={(e) => setForm({ ...form, body: e.target.value })}
        rows={4}
        className="mt-1"
        placeholder="Tell the HR team a little more…"
      />

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={send}
          disabled={escalation.isPending || form.subject.trim().length === 0}
        >
          {escalation.isPending ? "Sending…" : "Send to HR"}
        </Button>
      </div>
    </dialog>
  );
}
