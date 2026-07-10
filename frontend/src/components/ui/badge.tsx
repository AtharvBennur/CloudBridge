import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "destructive" | "secondary";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "bg-primary/10 text-primary",
    success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    warning: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    destructive: "bg-red-500/10 text-red-700 dark:text-red-400",
    secondary: "bg-muted text-muted-foreground",
  };

  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", variantClasses[variant], className)} {...props} />;
}
