import { FileText, ShieldCheck } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceStats } from "@/features/workspace/hooks/use-workspace-stats";
import { documentName } from "@/lib/format";

function DocumentList({ documents }: { documents: string[] }) {
  return (
    <ul className="mt-3 space-y-1.5">
      {documents.map((doc) => (
        <li key={doc} className="text-muted-foreground flex items-center gap-2 text-sm">
          <FileText className="size-3.5 shrink-0" />
          <span className="truncate">{documentName(doc)}</span>
        </li>
      ))}
    </ul>
  );
}

interface PolicyCoverageCardProps {
  /** Distinct documents cited in the open conversation. Undefined on the welcome screen. */
  citedDocuments?: string[];
}

/** Workspace pane: what the assistant's answers are grounded in. */
export function PolicyCoverageCard({ citedDocuments }: PolicyCoverageCardProps) {
  const stats = useWorkspaceStats();
  const inConversation = citedDocuments !== undefined;

  return (
    <div className="border-border bg-card rounded-xl border p-4">
      <div className="flex items-center gap-2 font-medium">
        <ShieldCheck className="text-primary size-4" />
        Policy coverage
      </div>
      <p className="text-muted-foreground mt-2 text-sm">
        Answers are grounded in your company&rsquo;s HR policies and handbook.
      </p>

      {inConversation ? (
        citedDocuments.length === 0 ? (
          <p className="text-muted-foreground mt-4 text-sm">
            No policies referenced yet.
          </p>
        ) : (
          <>
            <div className="text-muted-foreground mt-3 text-sm">
              {citedDocuments.length}{" "}
              {citedDocuments.length === 1 ? "policy" : "policies"} referenced in this
              conversation
            </div>
            <DocumentList documents={citedDocuments} />
          </>
        )
      ) : stats.isLoading ? (
        <div className="mt-4 space-y-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      ) : stats.isError || !stats.data ? (
        <p className="text-muted-foreground mt-4 text-sm">Source index unavailable.</p>
      ) : (
        <>
          <div className="text-muted-foreground mt-3 text-sm">
            {stats.data.documentCount}{" "}
            {stats.data.documentCount === 1 ? "policy" : "policies"} ·{" "}
            {stats.data.chunkCount.toLocaleString()} passages indexed
          </div>
          <DocumentList documents={stats.data.documents} />
        </>
      )}
    </div>
  );
}
