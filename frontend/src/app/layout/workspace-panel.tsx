import { PolicyCoverageCard } from "@/features/workspace/components/policy-coverage-card";

/** Right pane: policy coverage / groundedness / source index. */
export function WorkspacePanel() {
  return (
    <aside
      aria-label="Workspace"
      className="border-border bg-panel flex h-full flex-col gap-6 overflow-y-auto border-l p-5"
    >
      <div>
        <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
          Workspace
        </div>
        <div className="mt-1 text-lg font-semibold">HR help center</div>
      </div>

      <PolicyCoverageCard />
    </aside>
  );
}
