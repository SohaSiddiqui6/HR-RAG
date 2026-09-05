import { Sparkles } from "lucide-react";

/** Product identity shown at the top of the sidebar. */
export function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="bg-primary/15 text-primary flex size-9 items-center justify-center rounded-lg">
        <Sparkles className="size-4" />
      </div>
      <div className="leading-tight">
        <div className="text-sm font-semibold">Peoplewise</div>
        <div className="text-muted-foreground text-xs">HR assistant</div>
      </div>
    </div>
  );
}
