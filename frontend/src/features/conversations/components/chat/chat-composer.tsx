import { ArrowUp, Loader2 } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatComposerProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatComposer({ onSend, disabled = false }: ChatComposerProps) {
  const [draft, setDraft] = useState("");
  const canSend = draft.trim().length > 0 && !disabled;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSend) return;
    onSend(draft.trim());
    setDraft("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit(event);
    }
  }

  return (
    <form onSubmit={submit} className="border-border border-t p-4">
      <div className="border-input focus-within:ring-ring mx-auto flex max-w-3xl items-end gap-2 rounded-xl border p-2 focus-within:ring-2">
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder={
            disabled ? "Answering…" : "Ask about policies, benefits, time off…"
          }
          aria-label="Message"
          className="[field-sizing:content] max-h-40 resize-none border-0 bg-transparent px-2 py-1.5 focus-visible:ring-0"
        />
        <Button type="submit" size="icon" disabled={!canSend} aria-label="Send">
          {disabled ? <Loader2 className="animate-spin" /> : <ArrowUp />}
        </Button>
      </div>
    </form>
  );
}
