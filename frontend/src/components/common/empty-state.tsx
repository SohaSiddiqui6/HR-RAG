import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  className?: string;
}

/** Centred icon + copy for empty views (welcome screen, no results, ...). */
export function EmptyState({
  icon: Icon,
  title,
  description,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center gap-3 text-center", className)}>
      <div className="bg-primary/15 text-primary flex size-12 items-center justify-center rounded-xl">
        <Icon className="size-5" />
      </div>
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">{title}</h2>
        {description && (
          <p className="text-muted-foreground max-w-sm text-sm">{description}</p>
        )}
      </div>
    </div>
  );
}
