import { Activity, Database, LayoutDashboard, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Migrations", href: "/migrations", icon: Database },
  { label: "Health", href: "/dashboard", icon: Activity },
  { label: "Auth", href: "/dashboard", icon: ShieldCheck },
];

export function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 border-r bg-card/80 px-5 py-6 backdrop-blur lg:block">
      <div className="mb-9 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
          CB
        </div>
        <div>
          <p className="text-sm font-semibold">CloudBridge</p>
          <p className="text-xs text-muted-foreground">Sprint 3 Workspace</p>
        </div>
      </div>

      <nav className="space-y-1">
        {navigationItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.href}
            className={({ isActive }) =>
              cn(
                "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground",
                isActive && "bg-secondary text-secondary-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
