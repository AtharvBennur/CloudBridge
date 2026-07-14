import { ChevronLeft, ChevronRight, ClipboardCheck, Cloud, Database, LayoutDashboard, Server, Activity, GitCompare, Settings, ShieldCheck, Zap } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, category: "Main" },
  { label: "Migrations", href: "/migrations", icon: Database, category: "Main" },
  { label: "CDC Replication", href: "/cdc", icon: Zap, category: "Migration" },
  { label: "Schema Drift", href: "/schema-drift", icon: GitCompare, category: "Migration" },
  { label: "Approvals", href: "/approvals", icon: ShieldCheck, category: "Migration" },
  { label: "Databases", href: "/database-configs", icon: Server, category: "Infrastructure" },
  { label: "AWS Connections", href: "/aws-connections", icon: Cloud, category: "Infrastructure" },
  { label: "ECS Tasks", href: "/ecs", icon: Activity, category: "Infrastructure" },
  { label: "Pre-flight", href: "/preflight", icon: ClipboardCheck, category: "Infrastructure" },
  { label: "Observability", href: "/observability", icon: Activity, category: "Monitoring" },
  { label: "Notifications", href: "/notifications", icon: ShieldCheck, category: "Monitoring" },
  { label: "Rollback", href: "/rollback", icon: Settings, category: "Recovery" },
];

export function Sidebar({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: (value: boolean) => void }) {
  const categories = Array.from(new Set(navigationItems.map(item => item.category)));

  return (
    <aside className={cn("hidden shrink-0 border-r border-border/70 bg-gradient-to-b from-card/95 to-card/50 backdrop-blur-xl lg:flex", isCollapsed ? "w-20" : "w-72")}> 
      <div className="flex w-full flex-col px-4 py-6">
        <div className={cn("mb-8 flex items-center gap-3", isCollapsed && "justify-center")}> 
          <div className="relative grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-primary via-blue-500 to-indigo-600 text-sm font-bold text-primary-foreground shadow-xl shadow-primary/20">
            <span className="relative z-10">CB</span>
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/20 to-transparent" />
          </div>
          {!isCollapsed ? (
            <div>
              <p className="text-base font-semibold tracking-tight">CloudBridge</p>
              <p className="text-xs text-muted-foreground font-medium">Enterprise Platform</p>
            </div>
          ) : null}
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto">
          {categories.map((category) => (
            <div key={category} className="space-y-2">
              {!isCollapsed && (
                <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {category}
                </p>
              )}
              {navigationItems.filter(item => item.category === category).map((item) => (
                <NavLink
                  key={item.label}
                  to={item.href}
                  className={({ isActive }) =>
                    cn(
                      "group flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-all duration-200",
                      isActive 
                        ? "bg-primary/10 text-primary shadow-sm" 
                        : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
                      isCollapsed && "justify-center px-0",
                    )
                  }
                >
                  <item.icon className={cn("h-4 w-4 transition-colors", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                  {!isCollapsed ? (
                    <span className="transition-colors">{item.label}</span>
                  ) : null}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="mt-auto pt-6 border-t border-border/50">
          <Button 
            variant="ghost" 
            size="icon" 
            className="w-full justify-center hover:bg-muted/50" 
            onClick={() => onToggle(!isCollapsed)}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </aside>
  );
}
