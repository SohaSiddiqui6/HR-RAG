import { QueryClientProvider } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";

import { queryClient } from "@/app/query-client";

/** App-wide context: server-state cache and theme. Theme is fixed to dark for v1. */
export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
