import { useCallback, useState, createContext, useContext } from "react";
import { X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "success" | "destructive" | "warning" | "info";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = `toast-${++toastCounter}`;
      const newToast = { ...toast, id };
      setToasts((prev) => [...prev, newToast]);

      const duration = toast.duration ?? 4000;
      setTimeout(() => removeToast(id), duration);
    },
    [removeToast],
  );

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastViewport toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return { toast: ctx.addToast, dismiss: ctx.removeToast, toasts: ctx.toasts };
}

const variantStyles: Record<ToastVariant, string> = {
  default: "border-border/70 bg-card text-foreground",
  success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300",
  destructive: "border-red-500/30 bg-red-500/10 text-red-800 dark:text-red-300",
  warning: "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300",
  info: "border-sky-500/30 bg-sky-500/10 text-sky-800 dark:text-sky-300",
};

function ToastViewport({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  return (
    <div className="fixed bottom-4 right-4 z-[100] flex max-w-sm flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 80, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "group pointer-events-auto flex gap-3 rounded-xl border p-4 shadow-lg backdrop-blur-sm",
              variantStyles[t.variant ?? "default"],
            )}
          >
            <div className="flex-1">
              <p className="text-sm font-semibold">{t.title}</p>
              {t.description && <p className="mt-1 text-xs opacity-80">{t.description}</p>}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="shrink-0 rounded-md p-1 opacity-60 hover:opacity-100 transition"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
