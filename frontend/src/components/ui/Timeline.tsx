import { cn } from "@/lib/utils";
import { Clock } from "lucide-react";

interface TimelineItem {
  id: string;
  title: string;
  description?: string;
  timestamp: string;
  status?: "completed" | "pending" | "error";
  icon?: React.ReactNode;
}

interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

export function Timeline({ items, className }: TimelineProps) {
  return (
    <div className={cn("(space-y-6 before:absolute before:left-2 before:h-full before:w-0.5 before:-translate-x-1/2 before:bg-border relative", className)}>
      {items.map((item, index) => (
        <div key={item.id} className="relative pl-8">
          <div
            className={cn(
              "absolute left-0 top-1 h-4 w-4 rounded-full border-2 border-background",
              item.status === "completed" && "bg-emerald-500",
              item.status === "error" && "bg-red-500",
              item.status === "pending" && "bg-muted-foreground",
              !item.status && "bg-primary"
            )}
          />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              {item.icon && <span className="text-muted-foreground">{item.icon}</span>}
              <h4 className="font-semibold text-sm">{item.title}</h4>
            </div>
            {item.description && (
              <p className="text-sm text-muted-foreground">{item.description}</p>
            )}
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {new Date(item.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
