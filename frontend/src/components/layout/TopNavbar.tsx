import { Bell, LogOut, Menu, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export function TopNavbar({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: (value: boolean) => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-background/80 px-4 py-3 backdrop-blur md:px-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" className="hidden lg:inline-flex" onClick={() => onToggle(!isCollapsed)} aria-label="Collapse sidebar">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="hidden h-11 w-[min(36vw,420px)] items-center gap-2 rounded-2xl border border-border/70 bg-card/80 px-3 text-sm text-muted-foreground md:flex">
            <Search className="h-4 w-4" />
            <span>Search migrations, accounts, and health</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Notifications">
            <Bell className="h-4 w-4" />
          </Button>
          <ThemeToggle />
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium">{user?.displayName}</p>
            <p className="text-xs text-muted-foreground">{user?.email}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Sign out" title="Sign out">
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
