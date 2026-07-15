import React, { useState, useEffect, useCallback, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopNavbar } from "@/components/layout/TopNavbar";
import { websocketService } from "@/services/websocketService";
import { env } from "@/lib/env";

function ErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="max-w-md text-center space-y-4">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-red-500/10 flex items-center justify-center">
          <span className="text-2xl">!</span>
        </div>
        <h2 className="text-xl font-semibold text-foreground">Something went wrong</h2>
        <p className="text-sm text-muted-foreground">{error.message}</p>
        <button
          onClick={reset}
          className="inline-flex h-10 items-center justify-center rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

export class AppErrorBoundary extends React.Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode; fallback?: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return <ErrorFallback error={this.state.error} reset={this.reset} />;
    }
    return this.props.children;
  }
}

export function AppShell({ children }: { children: ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const location = useLocation();

  const closeMobileSidebar = useCallback(() => setIsMobileOpen(false), []);

  useEffect(() => {
    closeMobileSidebar();
  }, [location.pathname, closeMobileSidebar]);

  useEffect(() => {
    const wsUrl = env.wsBaseUrl;
    websocketService.connect(wsUrl).catch((error) => {
      console.error("Failed to connect to WebSocket:", error);
    });

    return () => {
      websocketService.disconnect();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.14),_transparent_28%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(248,250,252,1))] dark:bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.2),_transparent_30%),linear-gradient(135deg,_rgba(2,6,23,0.96),_rgba(15,23,42,1))]">
      <div className="flex min-h-screen">
        <Sidebar
          isCollapsed={isCollapsed}
          onToggle={setIsCollapsed}
          isMobileOpen={isMobileOpen}
          onMobileClose={closeMobileSidebar}
        />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopNavbar
            isCollapsed={isCollapsed}
            onToggle={setIsCollapsed}
            onMobileToggle={() => setIsMobileOpen((prev) => !prev)}
          />
          <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
