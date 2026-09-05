import { Outlet } from "react-router-dom";

import { Sidebar } from "@/app/layout/sidebar";
import { WorkspacePanel } from "@/app/layout/workspace-panel";

/** Three-pane shell: sidebar | chat (routed) | workspace. */
export function AppLayout() {
  return (
    <div className="bg-background text-foreground grid h-full grid-cols-[260px_1fr_340px]">
      <Sidebar />
      <main className="min-w-0">
        <Outlet />
      </main>
      <WorkspacePanel />
    </div>
  );
}
