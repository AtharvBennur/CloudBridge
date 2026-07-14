import { ChevronLeft, ChevronRight, ClipboardCheck, Cloud, Database, LayoutDashboard, Server } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Migrations", href: "/migrations", icon: Database },
  { label: "Databases", href: "/database-configs", icon: Server },
  { label: "AWS Connections", href: "/aws-connections", icon: Cloud },
  { label: "Pre-flight", href: "/preflight", icon: ClipboardCheck },
];

export function Sidebar({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: (value: boolean) => void }) {
  return (
    <aside className={cn("hidden shrink-0 border-r bg-card/80 backdrop-blur lg:flex", isCollapsed ? "w-20" : "w-72")}> 
      <div className="flex w-full flex-col px-4 py-5">
        <div className={cn("mb-8 flex items-center gap-3", isCollapsed && "justify-center")}> 
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-primary to-sky-500 text-sm font-bold text-primary-foreground shadow-lg">
            CB
          </div>
          {!isCollapsed ? (
            <div>
              <p className="text-sm font-semibold">CloudBridge</p>
              <p className="text-xs text-muted-foreground">Enterprise Console</p>
            </div>
          ) : null}
        </div>

        <nav className="space-y-1">
          {navigationItems.map((item) => (
            <NavLink
              key={item.label}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  "flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground",
                  isActive && "bg-primary/10 text-primary",
                  isCollapsed && "justify-center px-0",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {!isCollapsed ? <span>{item.label}</span> : null}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto pt-6">
          <Button variant="outline" size="icon" className="w-full justify-center" onClick={() => onToggle(!isCollapsed)}>
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </aside>
  );
}
