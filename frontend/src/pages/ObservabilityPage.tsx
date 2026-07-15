import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BarChart3, Activity, FileText, TrendingUp, AlertCircle, Clock, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { observabilityService } from "@/services/observabilityService";

export function ObservabilityPage() {
  const auditLogsQuery = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => observabilityService.getAuditLogs({ limit: 50 }),
  });

  const systemMetricsQuery = useQuery({
    queryKey: ["system-metrics"],
    queryFn: () => observabilityService.getSystemMetrics(),
  });

  const logs = auditLogsQuery.data || [];
  const metrics = systemMetricsQuery.data;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-indigo-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 p-3 text-white shadow-lg">
            <BarChart3 className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">Observability Console</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Monitor system health, audit logs, and migration metrics with real-time visibility.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <FileText className="mr-2 h-4 w-4" />
              Export Logs
            </Button>
            <Button size="sm">
              <TrendingUp className="mr-2 h-4 w-4" />
              View Metrics
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Total Migrations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">{metrics?.total_migrations || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">All time</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Running</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">{metrics?.running_migrations || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Active migrations</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">{metrics?.failed_migrations || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Requires attention</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Avg Duration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">{metrics?.avg_migration_duration_seconds ? `${Math.round(metrics.avg_migration_duration_seconds / 60)}m` : "0m"}</div>
            <p className="text-xs text-muted-foreground mt-1">Per migration</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Recent Audit Logs</CardTitle>
          <CardDescription>System events and user actions with full traceability</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {auditLogsQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!auditLogsQuery.isLoading && logs.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No audit logs recorded yet.
              </div>
            )}
            {!auditLogsQuery.isLoading && logs.slice(0, 10).map((log) => (
              <div key={log.id} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    log.severity === "CRITICAL" ? "bg-red-500/10 text-red-600" :
                    log.severity === "ERROR" ? "bg-orange-500/10 text-orange-600" :
                    log.severity === "WARNING" ? "bg-yellow-500/10 text-yellow-600" :
                    "bg-emerald-500/10 text-emerald-600"
                  }`}>
                    {log.severity === "CRITICAL" || log.severity === "ERROR" ? (
                      <AlertCircle className="h-5 w-5" />
                    ) : log.severity === "WARNING" ? (
                      <AlertCircle className="h-5 w-5" />
                    ) : (
                      <CheckCircle2 className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <h4 className="font-semibold">{log.event_type}</h4>
                    <p className="text-sm text-muted-foreground">{log.event_description}</p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      <span>{log.event_category}</span>
                      {log.user_email && <span>• {log.user_email}</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={log.severity === "CRITICAL" ? "destructive" : log.severity === "ERROR" ? "destructive" : log.severity === "WARNING" ? "warning" : "success"}>
                    {log.severity}
                  </Badge>
                  <div className="text-xs text-muted-foreground">
                    {new Date(log.occurred_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
