import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function StatCard({ title, value, change, icon: Icon, trend = "neutral", className }: StatCardProps) {
  const trendColors = {
    up: "text-emerald-600",
    down: "text-red-600",
    neutral: "text-muted-foreground",
  };

  return (
    <Card className={cn("border-border/70 shadow-sm hover:border-primary/45 transition", className)}>
      <CardContent className="pt-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
            {change && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className={trendColors[trend]}>{change}</span>
              </div>
            )}
          </div>
          {Icon && (
            <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
              <Icon className="h-4.5 w-4.5" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
