import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  Activity,
  FileText,
  BarChart,
  AlertCircle,
  CheckCircle2,
  Download,
  Loader2,
  Play,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { observabilityService } from "@/services/observabilityService";
import { migrationService } from "@/services/migrationService";
import { useToast } from "@/components/ui/toast";

export function ObservabilityPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [showMetrics, setShowMetrics] = useState(false);
  const [exporting, setExporting] = useState(false);

  const auditLogsQuery = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => observabilityService.getAuditLogs({ limit: 50 }),
  });

  const migrationsQuery = useQuery({
    queryKey: ["migrations"],
    queryFn: () => migrationService.list(),
  });

  const systemMetricsQuery = useQuery({
    queryKey: ["system-metrics"],
    queryFn: () => observabilityService.getSystemMetrics(),
  });

  const systemHealthQuery = useQuery({
    queryKey: ["system-health-metrics"],
    queryFn: () => observabilityService.getSystemMetrics(),
    enabled: showMetrics,
  });

  const logs = auditLogsQuery.data || [];
  const metrics = systemMetricsQuery.data;
  const migrations = migrationsQuery.data || [];

  const pendingMigrations = migrations.filter(m => m.status === "PENDING");
  const latestPendingMigration = pendingMigrations.length > 0 ? pendingMigrations[0] : null;

  const startMigrationMutation = useMutation({
    mutationFn: (migrationId: number) => {
      const migration = migrations.find((m) => m.id === migrationId);
      return migrationService.start(migrationId, migration?.aws_connection_id ?? undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migrations"] });
      toast({ title: "Migration started", description: "Migration is now running on Lambda", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to start migration", description: error.message, variant: "destructive" });
    },
  });

  const handleExportLogs = async () => {
    setExporting(true);
    try {
      const allLogs = await observabilityService.getAuditLogs({ limit: 1000 });
      const blob = new Blob([JSON.stringify(allLogs, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `audit-logs-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to export logs:", error);
    } finally {
      setExporting(false);
    }
  };

  const healthMetrics = systemHealthQuery.data;

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
            <h1 className="text-3xl font-semibold tracking-tight">
              Observability Console
            </h1>
            <p className="mt-2 text-base text-muted-foreground">
              Monitor system health, audit logs, and migration metrics with
              real-time visibility.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => navigate("/migrations/new")}
              className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
            >
              <Zap className="mr-2 h-4 w-4" />
              New Migration
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportLogs}
              disabled={exporting}
            >
              {exporting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Export Logs
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowMetrics(!showMetrics)}
            >
              <BarChart className="mr-2 h-4 w-4" />
              {showMetrics ? "Hide Metrics" : "View Metrics"}
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
            <div className="text-3xl font-semibold">
              {metrics?.migrations.total || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">All time</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-amber-600">
              {pendingMigrations.length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Ready to start
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Running</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">
              {metrics?.migrations.running || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Active migrations
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">
              {metrics?.migrations.failed || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Requires attention
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Avg Duration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">
              {"0m"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Per migration</p>
          </CardContent>
        </Card>
      </div>

      {latestPendingMigration && (
        <Card className="border-violet-500/50 bg-gradient-to-br from-violet-50/50 to-indigo-50/50 dark:from-violet-950/20 dark:to-indigo-950/20 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-violet-900 dark:text-violet-100">
              <Zap className="h-5 w-5 text-violet-600" />
              Ready to Start
            </CardTitle>
            <CardDescription>
              Latest pending migration ready for Lambda execution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">{latestPendingMigration.job_name}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  ID: {latestPendingMigration.id} • Created {new Date(latestPendingMigration.created_at).toLocaleDateString()}
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => startMigrationMutation.mutate(latestPendingMigration.id)}
                disabled={startMigrationMutation.isPending}
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
              >
                {startMigrationMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                Start Migration
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {showMetrics && (
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart className="h-5 w-5" />
              System Health Metrics
            </CardTitle>
            <CardDescription>
              Detailed system health breakdown
            </CardDescription>
          </CardHeader>
          <CardContent>
            {systemHealthQuery.isLoading ? (
              <div className="grid gap-4 md:grid-cols-4">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : healthMetrics ? (
              <div className="grid gap-4 md:grid-cols-4">
                <div className="p-4 rounded-xl border border-border/50">
                  <p className="text-xs text-muted-foreground">AWS Connections</p>
                  <p className="text-2xl font-semibold mt-1">
                    {healthMetrics.aws_connections.total}
                  </p>
                </div>
                <div className="p-4 rounded-xl border border-border/50">
                  <p className="text-xs text-muted-foreground">Database Configs</p>
                  <p className="text-2xl font-semibold mt-1">
                    {healthMetrics.database_configs.total}
                  </p>
                </div>
                <div className="p-4 rounded-xl border border-border/50">
                  <p className="text-xs text-muted-foreground">Active Lambda Functions</p>
                  <p className="text-2xl font-semibold mt-1">
                    {0}
                  </p>
                </div>
                <div className="p-4 rounded-xl border border-border/50">
                  <p className="text-xs text-muted-foreground">Audit Log Entries</p>
                  <p className="text-2xl font-semibold mt-1">
                    {0}
                  </p>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No metrics data available.
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Recent Audit Logs</CardTitle>
          <CardDescription>
            System events and user actions with full traceability
          </CardDescription>
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
            {!auditLogsQuery.isLoading &&
              logs.slice(0, 10).map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                        log.severity === "CRITICAL"
                          ? "bg-red-500/10 text-red-600"
                          : log.severity === "ERROR"
                          ? "bg-orange-500/10 text-orange-600"
                          : log.severity === "WARNING"
                          ? "bg-yellow-500/10 text-yellow-600"
                          : "bg-emerald-500/10 text-emerald-600"
                      }`}
                    >
                      {log.severity === "CRITICAL" ||
                      log.severity === "ERROR" ||
                      log.severity === "WARNING" ? (
                        <AlertCircle className="h-5 w-5" />
                      ) : (
                        <CheckCircle2 className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <h4 className="font-semibold">{log.event_type}</h4>
                      <p className="text-sm text-muted-foreground">
                        {log.event_description}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <span>{log.event_category}</span>
                        {log.user_email && <span>\u2022 {log.user_email}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge
                      variant={
                        log.severity === "CRITICAL"
                          ? "destructive"
                          : log.severity === "ERROR"
                          ? "destructive"
                          : log.severity === "WARNING"
                          ? "warning"
                          : "success"
                      }
                    >
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
