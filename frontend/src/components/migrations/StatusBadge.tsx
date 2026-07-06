/*
Purpose:
This file renders a visual badge for migration job statuses.

Why:
A consistent status chip makes the migration dashboard easier to scan.

Architecture:
Migration Pages
↓
Status Badge Component
*/

import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
}

const statusStyles: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
  RUNNING: "bg-sky-100 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300",
  COMPLETED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
  FAILED: "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalizedStatus = status.toUpperCase();
  const classes = statusStyles[normalizedStatus] || "bg-muted text-muted-foreground";

  return (
    <span className={cn("inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold", classes)}>
      {normalizedStatus}
    </span>
  );
}
