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
  iconColor?: string;
  iconBg?: string;
}

const defaultIconColors = [
  "from-blue-500 to-cyan-400",
  "from-violet-500 to-purple-400",
  "from-emerald-500 to-teal-400",
  "from-amber-500 to-orange-400",
  "from-rose-500 to-pink-400",
  "from-indigo-500 to-blue-400",
];

export function StatCard({ title, value, change, icon: Icon, trend = "neutral", className, iconColor, iconBg }: StatCardProps) {
  const trendColors = {
    up: "text-emerald-600",
    down: "text-red-600",
    neutral: "text-muted-foreground",
  };

  const trendIcons = {
    up: "\u2191",
    down: "\u2193",
    neutral: "\u2192",
  };

  const gradientClass = iconBg || `bg-gradient-to-br ${defaultIconColors[Math.abs(title.length) % defaultIconColors.length]}`;

  return (
    <Card className={cn("border-border/70 shadow-sm hover:shadow-lg hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-300 group", className)}>
      <CardContent className="pt-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
            {change && (
              <div className="mt-2 flex items-center gap-1.5 text-xs">
                <span className={cn(trendColors[trend], "font-medium")}>
                  {trendIcons[trend]} {change}
                </span>
              </div>
            )}
          </div>
          {Icon && (
            <div className={cn("rounded-xl p-2.5 text-white shadow-md group-hover:scale-110 group-hover:shadow-lg transition-all duration-300", gradientClass)}>
              <Icon className="h-4.5 w-4.5" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
