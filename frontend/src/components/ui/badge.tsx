import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "destructive" | "secondary" | "info" | "indigo" | "violet" | "rose" | "cyan" | "orange" | "teal" | "pink";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "bg-primary/10 text-primary",
    success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    warning: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    destructive: "bg-red-500/10 text-red-700 dark:text-red-400",
    secondary: "bg-muted text-muted-foreground",
    info: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
    indigo: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300",
    violet: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
    rose: "bg-rose-500/10 text-rose-700 dark:text-rose-300",
    cyan: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300",
    orange: "bg-orange-500/10 text-orange-700 dark:text-orange-300",
    teal: "bg-teal-500/10 text-teal-700 dark:text-teal-300",
    pink: "bg-pink-500/10 text-pink-700 dark:text-pink-300",
  };

  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", variantClasses[variant], className)} {...props} />;
}
