import { Outlet } from "react-router-dom";

import { ErrorBoundary } from "@/app/error-boundary";
import { Sidebar } from "@/app/layout/sidebar";
import { WorkspacePanel } from "@/app/layout/workspace-panel";

/** Three-pane shell: sidebar | chat (routed) | workspace. */
export function AppLayout() {
  return (
    <div className="bg-background text-foreground grid h-screen grid-cols-[260px_1fr_340px] grid-rows-1 overflow-hidden">
      <Sidebar />
      <main className="min-w-0 overflow-hidden" aria-label="Conversation">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <WorkspacePanel />
    </div>
  );
}
