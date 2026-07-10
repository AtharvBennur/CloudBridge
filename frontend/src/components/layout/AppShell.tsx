import { useState, type ReactNode } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopNavbar } from "@/components/layout/TopNavbar";

export function AppShell({ children }: { children: ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.14),_transparent_28%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(248,250,252,1))] dark:bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.2),_transparent_30%),linear-gradient(135deg,_rgba(2,6,23,0.96),_rgba(15,23,42,1))]">
      <div className="flex min-h-screen">
        <Sidebar isCollapsed={isCollapsed} onToggle={setIsCollapsed} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopNavbar isCollapsed={isCollapsed} onToggle={setIsCollapsed} />
          <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
