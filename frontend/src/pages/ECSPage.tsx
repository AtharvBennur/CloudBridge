import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Play,
  Server,
  Square,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  X,
  RefreshCw,
  Database,
  Clock,
  TrendingUp,
  Terminal,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ecsService } from "@/services/ecsService";
import { migrationService } from "@/services/migrationService";
import { awsConnectionService } from "@/services/awsConnectionService";
import { websocketService } from "@/services/websocketService";

export function ECSPage() {
  const queryClient = useQueryClient();
  const [selectedMigrationId, setSelectedMigrationId] = useState<number | null>(null);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const migrationsQuery = useQuery({
    queryKey: ["migrations-list"],
    queryFn: () => migrationService.list(),
  });

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  const ecsTasksQuery = useQuery({
    queryKey: ["ecs-tasks", selectedMigrationId],
    queryFn: () => ecsService.listTasks(selectedMigrationId!),
    enabled: !!selectedMigrationId,
    refetchInterval: 3000,
  });

  const migrationStatusQuery = useQuery({
    queryKey: ["migration-status", selectedMigrationId],
    queryFn: () => migrationService.getStatus(selectedMigrationId!),
    enabled: !!selectedMigrationId,
    refetchInterval: 3000,
  });

  // Reset local state when migration changes
  useEffect(() => {
    setLogs([]);
    setTaskStatus(null);
    setTaskError(null);
  }, [selectedMigrationId]);

  // Subscribe to WebSocket events for real-time updates
  useEffect(() => {
    if (!selectedMigrationId) return;

    websocketService.joinMigration(selectedMigrationId);

    const handleMigrationUpdate = (data: any) => {
      const updateData = data.data || data;

      // Handle log events
      if (updateData.type === "logs" && Array.isArray(updateData.logs)) {
        setLogs((prev) => [...prev, ...updateData.logs]);
        // Auto-scroll to bottom
        setTimeout(() => logsEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
      }

      // Handle status updates
      if (updateData.status) {
        setTaskStatus(updateData.status);
      }

      // Handle error updates
      if (updateData.error) {
        setTaskError(typeof updateData.error === "string" ? updateData.error : updateData.error.message || JSON.stringify(updateData.error));
      }

      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["migration-status", selectedMigrationId] });
      queryClient.invalidateQueries({ queryKey: ["ecs-tasks", selectedMigrationId] });
    };

    const handleECSTaskUpdate = (data: any) => {
      const updateData = data.data || data;
      if (updateData.status) {
        setTaskStatus(updateData.status);
      }
      if (updateData.error) {
        const err = updateData.error;
        setTaskError(err.reason || err.message || JSON.stringify(err));
      }
      queryClient.invalidateQueries({ queryKey: ["ecs-tasks", selectedMigrationId] });
    };

    websocketService.onMigrationProgress(handleMigrationUpdate);
    websocketService.onMigrationStatusChange(handleMigrationUpdate);
    websocketService.onECSTaskStatus(handleECSTaskUpdate);

    return () => {
      websocketService.leaveMigration(selectedMigrationId);
    };
  }, [selectedMigrationId, queryClient]);

  const showToast = (type: "success" | "error", message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  };

  const startMigrationMutation = useMutation({
    mutationFn: () => {
      if (!selectedMigrationId) throw new Error("No migration selected");
      return ecsService.startMigration(selectedMigrationId, selectedConnectionId ?? undefined);
    },
    onSuccess: (data) => {
      // Reset local state for fresh execution
      setLogs([]);
      setTaskStatus("RUNNING");
      setTaskError(null);

      queryClient.invalidateQueries({ queryKey: ["ecs-tasks", selectedMigrationId] });
      queryClient.invalidateQueries({ queryKey: ["migration-status", selectedMigrationId] });
      queryClient.invalidateQueries({ queryKey: ["migrations-list"] });
      showToast("success", "Migration started. Building worker image and launching ECS task...");
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.error?.message || error?.message || "Failed to start migration.";
      setTaskError(msg);
      showToast("error", msg);
    },
  });

  const stopTaskMutation = useMutation({
    mutationFn: (taskId: number) => ecsService.stopTask(taskId, "User stopped"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ecs-tasks", selectedMigrationId] });
      showToast("success", "Task stopped.");
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.error?.message || error?.message || "Failed to stop task.";
      showToast("error", msg);
    },
  });

  const retryTaskMutation = useMutation({
    mutationFn: (taskId: number) => ecsService.retryTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ecs-tasks", selectedMigrationId] });
      showToast("success", "Task retry initiated.");
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.error?.message || error?.message || "Failed to retry task.";
      showToast("error", msg);
    },
  });

  const tasks = ecsTasksQuery.data || [];
  const migrationStatus = migrationStatusQuery.data;
  const migrations = migrationsQuery.data || [];
  const awsConnections = awsConnectionsQuery.data || [];

  const selectedMigration = migrations.find((m) => m.id === selectedMigrationId);
  const selectedConnection = selectedConnectionId
    ? awsConnections.find((c) => c.id === selectedConnectionId)
    : null;

  // Get the latest task (most recent execution)
  const latestTask = tasks.length > 0 ? tasks[0] : null;

  const runningTasks = tasks.filter((t) => t.status === "RUNNING").length;
  const pendingTasks = tasks.filter((t) => t.status === "PENDING").length;
  const failedTasks = tasks.filter((t) => t.status === "FAILED").length;
  const completedTasks = tasks.filter((t) => t.status === "SUCCEEDED" || t.status === "STOPPED").length;

  const canStartMigration =
    selectedMigrationId !== null &&
    selectedMigration?.status !== "RUNNING" &&
    selectedMigration?.status !== "COMPLETED" &&
    selectedConnectionId !== null &&
    !startMigrationMutation.isPending;

  const startDisabledReason = !selectedMigrationId
    ? "Select a migration first"
    : selectedMigration?.status === "RUNNING"
      ? "Migration is already running"
      : selectedMigration?.status === "COMPLETED"
        ? "Migration already completed"
        : !selectedConnectionId
          ? "Select an AWS connection"
          : startMigrationMutation.isPending
            ? "Starting..."
            : "";

  // Determine effective status: prefer latest task status over migration status
  const effectiveStatus = taskStatus || migrationStatus?.status || selectedMigration?.status;
  const effectiveError = taskError || migrationStatus?.error_message;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Toast notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`fixed top-4 right-4 z-50 flex items-center gap-3 rounded-xl border px-4 py-3 shadow-lg ${
              toast.type === "success"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400"
            }`}
          >
            {toast.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertTriangle className="h-4 w-4 shrink-0" />
            )}
            <span className="text-sm font-medium">{toast.message}</span>
            <button onClick={() => setToast(null)} className="ml-2 opacity-60 hover:opacity-100">
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-emerald-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 p-3 text-white shadow-lg">
            <Activity className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">Migration Execution</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Launch database migrations on AWS ECS/Fargate. Resources are auto-discovered and tasks run in isolated containers.
            </p>
            <div className="mt-4 flex flex-wrap items-end gap-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-1 block">
                  Select Migration
                </label>
                <select
                  className="h-10 w-full max-w-xs rounded-xl border border-border/70 bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/20"
                  value={selectedMigrationId ?? ""}
                  onChange={(e) => setSelectedMigrationId(Number(e.target.value) || null)}
                >
                  <option value="">Choose a migration...</option>
                  {migrations.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.job_name} — {m.source_database} → {m.destination_database}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-1 block">
                  AWS Connection
                </label>
                <select
                  className="h-10 w-full max-w-xs rounded-xl border border-border/70 bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/20"
                  value={selectedConnectionId ?? ""}
                  onChange={(e) => setSelectedConnectionId(Number(e.target.value) || null)}
                >
                  <option value="">Choose a connection...</option>
                  {awsConnections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.aws_account_id} ({c.aws_region}) — {c.connection_status}
                    </option>
                  ))}
                </select>
              </div>

              {selectedMigration && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Badge variant={effectiveStatus === "RUNNING" ? "success" : effectiveStatus === "FAILED" ? "destructive" : "secondary"}>
                    {effectiveStatus || "UNKNOWN"}
                  </Badge>
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              disabled={!canStartMigration}
              title={startDisabledReason}
              onClick={() => startMigrationMutation.mutate()}
            >
              {startMigrationMutation.isPending ? (
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              ) : (
                <Play className="mr-2 h-5 w-5" />
              )}
              Start Migration
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Progress Panel */}
      {selectedMigrationId && migrationStatus && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-6 lg:grid-cols-3"
        >
          {/* Progress Card */}
          <Card className="border-border/70 shadow-sm lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-emerald-600" />
                Migration Progress
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-muted-foreground">Overall Progress</span>
                  <span className="font-semibold">{migrationStatus.progress_percent?.toFixed(1) ?? 0}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${migrationStatus.progress_percent ?? 0}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Rows Migrated</p>
                  <p className="text-xl font-semibold">{migrationStatus.rows_migrated?.toLocaleString() ?? 0}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Total Rows</p>
                  <p className="text-xl font-semibold">{migrationStatus.total_rows?.toLocaleString() ?? "—"}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Current Table</p>
                  <p className="text-xl font-semibold truncate">{migrationStatus.current_table ?? "—"}</p>
                </div>
              </div>

              {effectiveError && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">
                  <AlertTriangle className="h-4 w-4 inline mr-2" />
                  {effectiveError}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Status Card */}
          <Card className="border-border/70 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Started</span>
                <span className="text-sm font-medium ml-auto">
                  {migrationStatus.started_at ? new Date(migrationStatus.started_at).toLocaleTimeString() : "—"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Retries</span>
                <span className="text-sm font-medium ml-auto">{migrationStatus.retry_count ?? 0} / {migrationStatus.max_retries ?? 3}</span>
              </div>
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Chunk Size</span>
                <span className="text-sm font-medium ml-auto">{migrationStatus.chunk_size?.toLocaleString() ?? 1000}</span>
              </div>
              {latestTask && (
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Task</span>
                  <Badge variant={latestTask.status === "RUNNING" ? "success" : latestTask.status === "FAILED" ? "destructive" : "secondary"} className="ml-auto">
                    {latestTask.status}
                  </Badge>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Log Streaming Panel */}
      {selectedMigrationId && (effectiveStatus === "RUNNING" || logs.length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card className="border-border/70 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Terminal className="h-5 w-5 text-emerald-600" />
                Container Logs
                {effectiveStatus === "RUNNING" && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground ml-2" />
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 overflow-y-auto rounded-xl bg-gray-900 p-4 font-mono text-xs text-gray-100">
                {logs.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    {effectiveStatus === "RUNNING" ? "Waiting for logs..." : "No logs available"}
                  </div>
                ) : (
                  <>
                    {logs.map((line, i) => (
                      <div key={i} className="whitespace-pre-wrap break-all">
                        {line}
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Stats */}
      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Running</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">{runningTasks}</div>
            <p className="text-xs text-muted-foreground mt-1">Active Fargate tasks</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">{pendingTasks}</div>
            <p className="text-xs text-muted-foreground mt-1">Queued for execution</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">{failedTasks}</div>
            <p className="text-xs text-muted-foreground mt-1">Requires attention</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">{completedTasks}</div>
            <p className="text-xs text-muted-foreground mt-1">Total tasks finished</p>
          </CardContent>
        </Card>
      </div>

      {/* Task list */}
      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>ECS Tasks</CardTitle>
          <CardDescription>Fargate task execution history for this migration</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {!selectedMigrationId && (
              <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                Select a migration to view its ECS tasks.
              </div>
            )}

            {selectedMigrationId && ecsTasksQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}

            {selectedMigrationId && !ecsTasksQuery.isLoading && tasks.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No ECS tasks yet. Click{" "}
                <span className="font-medium text-primary">Start Migration</span>{" "}
                to launch the first Fargate task.
              </div>
            )}

            {selectedMigrationId &&
              !ecsTasksQuery.isLoading &&
              tasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                        task.status === "RUNNING"
                          ? "bg-emerald-500/10 text-emerald-600"
                          : task.status === "PENDING"
                            ? "bg-orange-500/10 text-orange-600"
                            : task.status === "STOPPED" || task.status === "SUCCEEDED"
                              ? "bg-gray-500/10 text-gray-600"
                              : "bg-red-500/10 text-red-600"
                      }`}
                    >
                      {task.status === "RUNNING" || task.status === "PENDING" ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <Server className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <h4 className="font-semibold">
                        {task.task_definition_arn?.split("/").pop() || `Task #${task.id}`}
                      </h4>
                      <p className="text-sm text-muted-foreground">
                        Cluster: {task.cluster_arn?.split("/").pop() || "auto-discovered"}
                      </p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                        <span>CPU: {task.cpu}</span>
                        <span>Memory: {task.memory}MB</span>
                        <span>Type: {task.launch_type}</span>
                        {task.retry_count > 0 && <span>Retries: {task.retry_count}</span>}
                      </div>
                      {task.reason && (
                        <p className="text-xs text-red-600 mt-1">{task.reason}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge
                      variant={
                        task.status === "RUNNING"
                          ? "success"
                          : task.status === "PENDING"
                            ? "info"
                            : task.status === "STOPPED" || task.status === "SUCCEEDED"
                              ? "secondary"
                              : "destructive"
                      }
                    >
                      {task.status}
                    </Badge>
                    <div className="flex gap-2">
                      {task.status === "RUNNING" ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => stopTaskMutation.mutate(task.id)}
                          title="Stop task"
                        >
                          <Square className="h-4 w-4" />
                        </Button>
                      ) : task.status === "FAILED" ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => retryTaskMutation.mutate(task.id)}
                          title="Retry task"
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                      ) : null}
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
