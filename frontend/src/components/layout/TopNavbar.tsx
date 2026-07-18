import { Bell, LogOut, Menu, ChevronDown, User, Settings, AlertCircle, Info, CheckCircle } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { CommandPalette } from "@/components/ui/command-palette";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { notificationService, type Notification } from "@/services/notificationService";

function formatTimestamp(date: Date) {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

function getNotificationIcon(type: string) {
  switch (type) {
    case "success":
    case "SENT":
      return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    case "error":
    case "FAILED":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case "warning":
      return <AlertCircle className="h-4 w-4 text-amber-500" />;
    default:
      return <Info className="h-4 w-4 text-blue-500" />;
  }
}

function useClickOutside(ref: React.RefObject<HTMLElement | null>, handler: () => void, enabled: boolean) {
  useEffect(() => {
    if (!enabled) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        handler();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [ref, handler, enabled]);
}

export function TopNavbar({
  isCollapsed,
  onToggle,
  onMobileToggle,
}: {
  isCollapsed: boolean;
  onToggle: (value: boolean) => void;
  onMobileToggle?: () => void;
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  useClickOutside(profileRef, () => setShowProfileMenu(false), showProfileMenu);
  useClickOutside(notifRef, () => setShowNotifications(false), showNotifications);

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const markAsRead = (id: number) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, status: "SENT" as const } : n)));
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, status: "SENT" as const })));
  };

  const unreadCount = notifications.filter((n) => n.status !== "SENT").length;

  useEffect(() => {
    notificationService
      .getHistory({ limit: 20 })
      .then((data) => setNotifications(data))
      .catch(() => {});
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-gradient-to-b from-background/95 to-background/80 px-4 py-3 backdrop-blur-xl md:px-6">
      {/* Subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
            onClick={onMobileToggle}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="hidden lg:inline-flex hover:bg-muted/50"
            onClick={() => onToggle(!isCollapsed)}
            aria-label="Collapse sidebar"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <CommandPalette />
        </div>

        <div className="flex items-center gap-2">
          <div className="relative" ref={notifRef}>
            <Button
              variant="ghost"
              size="icon"
              className="relative hover:bg-muted/50 transition-transform hover:scale-105"
              aria-label="Notifications"
              onClick={() => setShowNotifications(!showNotifications)}
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-gradient-to-r from-rose-500 to-red-500 animate-pulse-soft" />
              )}
            </Button>

            {showNotifications && (
              <div className="absolute right-0 top-12 w-96 rounded-xl border border-border/70 bg-background/95 backdrop-blur-xl shadow-soft p-2 animate-scale-in">
                <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 mb-2">
                  <h3 className="font-semibold text-sm">Notifications</h3>
                  {unreadCount > 0 && (
                    <Button variant="ghost" size="sm" className="h-7 text-xs text-primary hover:text-primary/80" onClick={markAllAsRead}>
                      Mark all read
                    </Button>
                  )}
                </div>
                <div className="max-h-80 overflow-y-auto space-y-1">
                  {notifications.length === 0 ? (
                    <div className="py-8 text-center text-sm text-muted-foreground">No notifications</div>
                  ) : (
                    notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={cn(
                          "p-3 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors",
                          notification.status !== "SENT" && "bg-muted/30",
                        )}
                        onClick={() => {
                          markAsRead(notification.id);
                          setShowNotifications(false);
                        }}
                      >
                        <div className="flex items-start gap-3">
                          {getNotificationIcon(notification.status)}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-sm font-medium text-foreground truncate">{notification.subject}</p>
                              {notification.status !== "SENT" && (
                                <div className="h-2 w-2 rounded-full bg-primary flex-shrink-0" />
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{notification.body}</p>
                            <p className="text-xs text-muted-foreground/60 mt-1">
                              {formatTimestamp(new Date(notification.created_at))}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="border-t border-border/50 mt-2 pt-2">
                  <Button
                    variant="ghost"
                    className="w-full justify-center h-9 text-sm"
                    onClick={() => {
                      setShowNotifications(false);
                      navigate("/notifications");
                    }}
                  >
                    View all notifications
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="hidden md:flex items-center gap-3 pl-2 border-l border-border/50 relative" ref={profileRef}>
            <Button
              variant="ghost"
              className="flex items-center gap-2 h-10 px-2 hover:bg-muted/50"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
            >
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-500 via-indigo-500 to-blue-500 flex items-center justify-center text-sm font-semibold text-white shadow-md ring-2 ring-white/20 dark:ring-white/10 transition-transform hover:scale-105">
                {user?.displayName?.charAt(0) || "?"}
              </div>
              <ChevronDown className="h-4 w-4" />
            </Button>

            {showProfileMenu && (
              <div className="absolute right-0 top-12 w-56 rounded-xl border border-border/70 bg-background/95 backdrop-blur-xl shadow-soft p-2 animate-scale-in">
                <div className="px-3 py-2 border-b border-border/50 mb-2">
                  <p className="text-sm font-medium text-foreground">{user?.displayName || "User"}</p>
                  <p className="text-xs text-muted-foreground">{user?.email || ""}</p>
                </div>
                <div className="space-y-1">
                  <Button
                    variant="ghost"
                    className="w-full justify-start h-9"
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate("/account");
                    }}
                  >
                    <User className="h-4 w-4 mr-2" />
                    Account
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start h-9"
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate("/settings");
                    }}
                  >
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </Button>
                  <div className="border-t border-border/50 my-1" />
                  <Button
                    variant="ghost"
                    className="w-full justify-start h-9 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                    onClick={handleLogout}
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign out
                  </Button>
                </div>
              </div>
            )}
          </div>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
