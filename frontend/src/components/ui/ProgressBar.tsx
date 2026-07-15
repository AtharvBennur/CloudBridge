import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  color?: "primary" | "success" | "warning" | "destructive";
}

export function ProgressBar({ value, max = 100, className, showLabel = false, size = "md", color = "primary" }: ProgressBarProps) {
  const percentage = Math.min((value / max) * 100, 100);
  
  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3",
  };

  const colorClasses = {
    primary: "bg-primary",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    destructive: "bg-red-500",
  };

  return (
    <div className={cn("w-full", className)}>
      <div className={cn("relative w-full overflow-hidden rounded-full bg-muted", sizeClasses[size])}>
        <div
          className={cn("h-full transition-all duration-500 ease-out", colorClasses[color])}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{value.toLocaleString()}</span>
          <span>{max.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
