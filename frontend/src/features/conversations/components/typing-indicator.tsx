import { Sparkles } from "lucide-react";

/** Shown as the last item in the list while an answer is being generated. */
export function TypingIndicator() {
  return (
    <div className="flex gap-3" aria-label="Assistant is typing">
      <div className="bg-primary/15 text-primary mt-1 flex size-7 shrink-0 items-center justify-center rounded-lg">
        <Sparkles className="size-3.5" />
      </div>
      <div className="border-border bg-card flex items-center gap-1 rounded-xl border px-4 py-4">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="bg-muted-foreground size-1.5 animate-bounce rounded-full"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
