import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "border-input placeholder:text-muted-foreground focus-visible:ring-ring flex w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
