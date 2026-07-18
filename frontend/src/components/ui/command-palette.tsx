import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  LayoutDashboard,
  Database,
  Cloud,
  Server,
  Activity,
  Settings,
  Bell,
  BarChart3,
  GitCompare,
  ShieldCheck,
  RotateCcw,
  Zap,
  ClipboardCheck,
  User,
  HelpCircle,
  Plus,
  ArrowRight,
} from "lucide-react";

interface CommandItem {
  label: string;
  description?: string;
  icon: typeof Search;
  href?: string;
  action?: () => void;
  keywords?: string[];
}

const commands: CommandItem[] = [
  { label: "Dashboard", description: "Overview and metrics", icon: LayoutDashboard, href: "/dashboard", keywords: ["home", "overview"] },
  { label: "Migrations", description: "View all migration jobs", icon: Database, href: "/migrations", keywords: ["list", "jobs"] },
  { label: "Create Migration", description: "Start a new migration wizard", icon: Plus, href: "/migrations/new", keywords: ["new", "add", "create"] },
  { label: "CDC Replication", description: "Change data capture settings", icon: Zap, href: "/cdc", keywords: ["cdc", "replication", "change"] },
  { label: "Schema Drift", description: "Monitor schema changes", icon: GitCompare, href: "/schema-drift", keywords: ["schema", "drift", "compare"] },
  { label: "Approvals", description: "Schema approval queue", icon: ShieldCheck, href: "/approvals", keywords: ["approve", "schema"] },
  { label: "Rollback", description: "Migration rollback controls", icon: RotateCcw, href: "/rollback", keywords: ["rollback", "undo"] },
  { label: "Databases", description: "Database endpoint configurations", icon: Server, href: "/database-configs", keywords: ["database", "db", "endpoint"] },
  { label: "AWS Connections", description: "Manage AWS account connections", icon: Cloud, href: "/aws-connections", keywords: ["aws", "cloud", "iam"] },
  { label: "ECS Tasks", description: "View ECS task execution", icon: Activity, href: "/ecs", keywords: ["ecs", "fargate", "tasks"] },
  { label: "Pre-flight Checks", description: "Run pre-migration validation", icon: ClipboardCheck, href: "/preflight", keywords: ["preflight", "validate", "check"] },
  { label: "Observability", description: "Audit logs and metrics", icon: BarChart3, href: "/observability", keywords: ["logs", "metrics", "monitor"] },
  { label: "Notifications", description: "Notification center", icon: Bell, href: "/notifications", keywords: ["alerts", "notify"] },
  { label: "Account", description: "User account settings", icon: User, href: "/account", keywords: ["profile", "user"] },
  { label: "Settings", description: "Application settings", icon: Settings, href: "/settings", keywords: ["config", "preferences"] },
  { label: "Help", description: "Documentation and support", icon: HelpCircle, href: "/help", keywords: ["docs", "support"] },
];

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        setQuery("");
      }
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
        setQuery("");
      }
    },
    [isOpen],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const filtered = useMemo(() => {
    if (!query.trim()) return commands;
    const lower = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(lower) ||
        cmd.description?.toLowerCase().includes(lower) ||
        cmd.keywords?.some((k) => k.includes(lower)),
    );
  }, [query]);

  const handleSelect = (item: CommandItem) => {
    setIsOpen(false);
    setQuery("");
    if (item.href) {
      navigate(item.href);
    } else if (item.action) {
      item.action();
    }
  };

  return (
    <>
      {/* Keyboard shortcut hint in search bar */}
      <button
        onClick={() => { setIsOpen(true); setQuery(""); }}
        className="hidden md:flex items-center gap-2 rounded-xl border border-border/50 bg-muted/30 px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/50 transition"
      >
        <Search className="h-3.5 w-3.5" />
        <span>Search...</span>
        <kbd className="pointer-events-none ml-4 inline-flex h-5 select-none items-center gap-1 rounded border border-border/50 bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm"
              onClick={() => { setIsOpen(false); setQuery(""); }}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              transition={{ duration: 0.15 }}
              className="fixed left-1/2 top-[20%] z-[70] w-full max-w-lg -translate-x-1/2 rounded-2xl border border-border/70 bg-card shadow-2xl"
            >
              <div className="flex items-center gap-3 border-b border-border/50 px-4">
                <Search className="h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent py-4 text-sm outline-none placeholder:text-muted-foreground"
                  autoFocus
                />
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-border/50 bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                  ESC
                </kbd>
              </div>
              <div className="max-h-80 overflow-y-auto p-2">
                {filtered.length === 0 && (
                  <div className="py-6 text-center text-sm text-muted-foreground">
                    No results found for "{query}"
                  </div>
                )}
                {filtered.map((item) => (
                  <button
                    key={item.label}
                    onClick={() => handleSelect(item)}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm hover:bg-muted/50 transition-colors text-left"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/50">
                      <item.icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{item.label}</p>
                      {item.description && <p className="text-xs text-muted-foreground">{item.description}</p>}
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50" />
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
