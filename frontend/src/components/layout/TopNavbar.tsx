import { Bell, LogOut, Menu, Search, ChevronDown, HelpCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

export function TopNavbar({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: (value: boolean) => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-gradient-to-b from-background/95 to-background/80 px-4 py-3 backdrop-blur-xl md:px-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" className="hidden lg:inline-flex hover:bg-muted/50" onClick={() => onToggle(!isCollapsed)} aria-label="Collapse sidebar">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="hidden h-11 w-[min(36vw,420px)] items-center gap-3 rounded-2xl border border-border/70 bg-card/80 px-4 text-sm text-muted-foreground shadow-sm transition-all focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 md:flex">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search migrations, accounts, and health..." 
              className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground/60"
            />
            <kbd className="hidden h-6 items-center gap-1 rounded border border-border/50 bg-muted/50 px-2 text-xs font-medium text-muted-foreground sm:flex">
              <span>⌘</span>
              <span>K</span>
            </kbd>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="relative hover:bg-muted/50" aria-label="Notifications">
            <Bell className="h-4 w-4" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500" />
          </Button>
          <Button variant="ghost" size="icon" className="hover:bg-muted/50" aria-label="Help">
            <HelpCircle className="h-4 w-4" />
          </Button>
          <div className="hidden md:flex items-center gap-3 pl-2 border-l border-border/50">
            <div className="text-right">
              <p className="text-sm font-medium text-foreground">{user?.displayName || "Admin User"}</p>
              <p className="text-xs text-muted-foreground">{user?.email || "admin@cloudbridge.io"}</p>
            </div>
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary to-blue-500 flex items-center justify-center text-sm font-semibold text-primary-foreground shadow-md">
              {user?.displayName?.charAt(0) || "A"}
            </div>
            <Button variant="ghost" size="icon" className="hover:bg-muted/50" onClick={handleLogout} aria-label="Sign out" title="Sign out">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
