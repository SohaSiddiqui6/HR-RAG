import { Component, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/** Catches render errors below it and shows a recoverable fallback, not a blank page. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error("Unhandled UI error:", error);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
        <div>
          <h2 className="font-medium">Something went wrong</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            The page hit an unexpected error.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
          Reload
        </Button>
      </div>
    );
  }
}
