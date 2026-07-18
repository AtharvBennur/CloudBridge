import { ChevronLeft, ChevronRight, ClipboardCheck, Cloud, Database, LayoutDashboard, Server, Activity, GitCompare, Settings, ShieldCheck, Zap, BarChart3, RotateCcw, User } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, category: "Overview", color: "text-blue-500" },
  { label: "Migrations", href: "/migrations", icon: Database, category: "Overview", color: "text-violet-500" },
  { label: "CDC Replication", href: "/cdc", icon: Zap, category: "Data", color: "text-amber-500" },
  { label: "Schema Drift", href: "/schema-drift", icon: GitCompare, category: "Data", color: "text-rose-500" },
  { label: "Approvals", href: "/approvals", icon: ShieldCheck, category: "Data", color: "text-emerald-500" },
  { label: "Rollback", href: "/rollback", icon: RotateCcw, category: "Data", color: "text-orange-500" },
  { label: "Databases", href: "/database-configs", icon: Server, category: "Infrastructure", color: "text-cyan-500" },
  { label: "AWS Connections", href: "/aws-connections", icon: Cloud, category: "Infrastructure", color: "text-indigo-500" },
  { label: "ECS Tasks", href: "/ecs", icon: Activity, category: "Infrastructure", color: "text-pink-500" },
  { label: "Pre-flight", href: "/preflight", icon: ClipboardCheck, category: "Infrastructure", color: "text-teal-500" },
  { label: "Observability", href: "/observability", icon: BarChart3, category: "Monitoring", color: "text-purple-500" },
];

const secondaryNavItems = [
  { label: "Account", href: "/account", icon: User },
  { label: "Settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: (value: boolean) => void;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

function SidebarContent({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: (value: boolean) => void }) {
  const categories = Array.from(new Set(navigationItems.map((item) => item.category)));

  return (
    <div className="flex w-full flex-col px-4 py-6 h-full">
      <div className={cn("mb-8 flex items-center gap-3", isCollapsed && "justify-center")}>
        <div className="relative">
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary to-blue-500 blur-lg opacity-50" />
          <div className="relative grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-primary to-blue-500 text-white shadow-xl shadow-primary/20">
            <Cloud className="h-5 w-5" />
          </div>
        </div>
        {!isCollapsed ? (
          <div>
            <p className="text-base font-semibold tracking-tight">CloudBridge</p>
            <p className="text-xs text-muted-foreground font-medium">Enterprise Migration</p>
          </div>
        ) : null}
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto">
        {categories.map((category) => (
          <div key={category} className="space-y-2">
            {!isCollapsed && (
              <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">{category}</p>
            )}
            {navigationItems
              .filter((item) => item.category === category)
              .map((item) => (
                <NavLink
                  key={item.label}
                  to={item.href}
                  className={({ isActive }) =>
                    cn(
                      "group flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-all duration-200",
                      isActive
                        ? "bg-gradient-to-r from-primary/10 to-blue-500/5 text-primary shadow-sm"
                        : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
                      isCollapsed && "justify-center px-0",
                    )
                  }
                >
                  {({ isActive }: { isActive: boolean }) => (
                    <>
                      <div className={cn("rounded-lg p-1.5 transition-all duration-200", isActive ? "bg-primary/15 scale-110" : "bg-transparent group-hover:bg-muted/60 group-hover:scale-105")}>
                        <item.icon
                          className={cn("h-4 w-4 transition-all duration-200", isActive ? item.color : "text-muted-foreground group-hover:text-foreground")}
                        />
                      </div>
                      {!isCollapsed ? <span className="transition-colors">{item.label}</span> : null}
                    </>
                  )}
                </NavLink>
              ))}
          </div>
        ))}
      </nav>

      <div className="mt-auto pt-4 border-t border-border/50 space-y-2">
        {secondaryNavItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.href}
            className={({ isActive }) =>
              cn(
                "group flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-all duration-200",
                isActive ? "bg-primary/10 text-primary shadow-sm" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
                isCollapsed && "justify-center px-0",
              )
            }
          >
            {({ isActive }: { isActive: boolean }) => (
              <>
                <item.icon className={cn("h-4 w-4 transition-colors", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                {!isCollapsed ? <span className="transition-colors">{item.label}</span> : null}
              </>
            )}
          </NavLink>
        ))}
        <Button
          variant="ghost"
          size="icon"
          className="w-full justify-center hover:bg-muted/50 transition-transform hover:scale-105"
          onClick={() => onToggle(!isCollapsed)}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}

export function Sidebar({ isCollapsed, onToggle, isMobileOpen, onMobileClose }: SidebarProps) {
  useEffect(() => {
    if (isMobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobileOpen]);

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden shrink-0 border-r border-border/70 bg-gradient-to-b from-card/95 to-card/50 backdrop-blur-xl lg:flex",
          isCollapsed ? "w-20" : "w-72",
        )}
      >
        <SidebarContent isCollapsed={isCollapsed} onToggle={onToggle} />
      </aside>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onMobileClose} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-gradient-to-b from-card to-card/95 backdrop-blur-xl border-r border-border/70 shadow-2xl animate-slide-in-left">
            <SidebarContent isCollapsed={false} onToggle={() => onMobileClose?.()} />
          </aside>
        </div>
      )}
    </>
  );
}
