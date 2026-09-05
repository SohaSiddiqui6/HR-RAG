import { ShieldCheck } from "lucide-react";

/** Right pane: policy coverage / groundedness / source index. Data lands in Step 5. */
export function WorkspacePanel() {
  return (
    <aside className="border-border bg-panel flex h-full flex-col gap-6 border-l p-5">
      <div>
        <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
          Workspace
        </div>
        <div className="mt-1 text-lg font-semibold">HR help center</div>
      </div>

      <div className="border-border bg-card rounded-xl border p-4">
        <div className="flex items-center gap-2 font-medium">
          <ShieldCheck className="text-primary size-4" />
          Policy coverage
        </div>
        <p className="text-muted-foreground mt-2 text-sm">
          Answers are grounded in your company&rsquo;s latest HR policies and handbook.
        </p>
        <div className="mt-3 flex items-center gap-2 text-sm">
          <span className="bg-primary size-1.5 rounded-full" />
          <span className="text-muted-foreground">Source index loading&hellip;</span>
        </div>
      </div>
    </aside>
  );
}
