import { FileText, ShieldCheck } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceStats } from "@/features/workspace/hooks/use-workspace-stats";
import { documentName } from "@/lib/format";

/** Workspace pane: what the assistant's answers are grounded in. */
export function PolicyCoverageCard() {
  const { data, isLoading, isError } = useWorkspaceStats();

  return (
    <div className="border-border bg-card rounded-xl border p-4">
      <div className="flex items-center gap-2 font-medium">
        <ShieldCheck className="text-primary size-4" />
        Policy coverage
      </div>
      <p className="text-muted-foreground mt-2 text-sm">
        Answers are grounded in your company&rsquo;s HR policies and handbook.
      </p>

      {isLoading ? (
        <div className="mt-4 space-y-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      ) : isError || !data ? (
        <p className="text-muted-foreground mt-4 text-sm">Source index unavailable.</p>
      ) : (
        <>
          <div className="text-muted-foreground mt-3 text-sm">
            {data.documentCount} {data.documentCount === 1 ? "policy" : "policies"} ·{" "}
            {data.chunkCount.toLocaleString()} passages indexed
          </div>
          <ul className="mt-3 space-y-1.5">
            {data.documents.map((doc) => (
              <li
                key={doc}
                className="text-muted-foreground flex items-center gap-2 text-sm"
              >
                <FileText className="size-3.5 shrink-0" />
                <span className="truncate">{documentName(doc)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
