import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";

import { submitFeedback } from "@/features/conversations/api/feedback";
import { cn } from "@/lib/cn";

/** Thumbs up/down on an assistant answer — recorded in Langfuse against its trace. */
export function MessageFeedback({ traceId }: { traceId: string }) {
  const [rating, setRating] = useState<"up" | "down" | null>(null);

  function rate(value: "up" | "down") {
    setRating(value);
    void submitFeedback(traceId, value === "up");
  }

  return (
    <div className="mt-2 flex gap-0.5">
      {(["up", "down"] as const).map((value) => {
        const Icon = value === "up" ? ThumbsUp : ThumbsDown;
        return (
          <button
            key={value}
            type="button"
            aria-label={value === "up" ? "Helpful" : "Not helpful"}
            aria-pressed={rating === value}
            onClick={() => rate(value)}
            className={cn(
              "text-muted-foreground hover:text-foreground rounded p-1 transition-colors",
              rating === value && "text-foreground",
            )}
          >
            <Icon className="size-3.5" />
          </button>
        );
      })}
    </div>
  );
}
