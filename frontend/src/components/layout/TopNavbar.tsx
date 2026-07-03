import { LogOut, Menu, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export function TopNavbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-20 border-b bg-background/88 px-4 py-3 backdrop-blur md:px-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="hidden h-10 w-[min(36vw,420px)] items-center gap-2 rounded-md border bg-card px-3 text-sm text-muted-foreground md:flex">
            <Search className="h-4 w-4" />
            <span>Search foundation assets</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
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
