/*
Purpose:
This file displays a single migration job in detail.

Why:
Users need a high-level view of metadata and status for one migration job.

Architecture:
Protected App Shell
↓
Migration Detail Page
↓
Migration Service
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Database, CalendarDays, FolderKanban, Play, Pause, RotateCcw, X, Terminal, Layers, Zap, CheckCircle2, AlertCircle } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/migrations/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { migrationService } from "@/services/migrationService";
import { preflightService } from "@/services/preflightService";
import { useToast } from "@/components/ui/toast";
import { websocketService } from "@/services/websocketService";
import { env } from "@/lib/env";
import { ProgressBar } from "@/components/ui/ProgressBar";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export function MigrationDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const migrationId = Number(id);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [logs, setLogs] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // WebSocket connection for real-time logs
  useEffect(() => {
    if (!Number.isFinite(migrationId)) return;

    const wsUrl = env.wsBaseUrl;
    websocketService.connect(wsUrl)
      .then(() => {
        setIsConnected(true);
        websocketService.joinMigration(migrationId);
        
        // Listen for migration updates including logs
        websocketService.onAllMigrationUpdates((payload) => {
          if (payload.data?.type === "logs" && payload.data?.logs) {
            setLogs(prev => [...prev, ...payload.data.logs]);
          }
          
          if (payload.data?.message) {
            setLogs(prev => [...prev, `[${new Date(payload.timestamp || Date.now()).toLocaleTimeString()}] ${payload.data.message}`]);
          }
          
          if (payload.data?.error_message) {
            setLogs(prev => [...prev, `[${new Date(payload.timestamp || Date.now()).toLocaleTimeString()}] ERROR: ${payload.data.error_message}`]);
          }

          // Invalidate the query to fetch the latest state whenever an update is received
          queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
        });
      })
      .catch((error) => {
        console.error("WebSocket connection failed:", error);
      });

    return () => {
      websocketService.leaveMigration(migrationId);
      websocketService.disconnect();
    };
  }, [migrationId]);

  const migrationQuery = useQuery({
    queryKey: ["migration", migrationId],
    queryFn: () => migrationService.getById(migrationId),
    enabled: Number.isFinite(migrationId),
    refetchInterval: 2000, // Poll every 2 seconds when migration is running
  });

  const startMutation = useMutation({
    mutationFn: async () => {
      const awsConnectionId = migrationQuery.data?.aws_connection_id ?? undefined;
      if (awsConnectionId === undefined) {
        throw new Error("No AWS connection is linked to this migration.");
      }
      const readiness = await preflightService.checkLambdaReadiness({ aws_connection_id: awsConnectionId });
      const blocked = Object.entries(readiness.functions).filter(([, value]) => value.status !== "READY");
      if (blocked.length > 0) {
        const message = blocked.map(([name, value]) => `${name}: ${value.message}`).join(" • ");
        throw new Error(message);
      }
      return migrationService.start(migrationId, awsConnectionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration started", description: "Migration is now running on Lambda", variant: "success" });
    },
    onError: (error: any) => {
      const backendMessage = error?.response?.data?.error?.message || error?.message || "Failed to start migration.";
      toast({ title: "Failed to start migration", description: backendMessage, variant: "destructive" });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => migrationService.pause(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration paused", description: "Migration has been paused", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to pause migration", description: error.message, variant: "destructive" });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => migrationService.resume(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration resumed", description: "Migration has been resumed", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to resume migration", description: error.message, variant: "destructive" });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => migrationService.cancel(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration cancelled", description: "Migration has been cancelled", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to cancel migration", description: error.message, variant: "destructive" });
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => migrationService.retry(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration retry initiated", description: "Migration will be retried", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to retry migration", description: error.message, variant: "destructive" });
    },
  });

  if (migrationQuery.isLoading) {
    return <div className="rounded-lg border border-dashed p-8 text-sm text-muted-foreground">Loading migration details…</div>;
  }

  if (migrationQuery.isError || !migrationQuery.data) {
    return (
      <div className="space-y-4">
        <Button variant="outline" onClick={() => navigate("/migrations")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to migrations
        </Button>
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {migrationQuery.error instanceof Error ? migrationQuery.error.message : "Unable to load migration job."}
        </div>
      </div>
    );
  }

  const migration = migrationQuery.data;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Button variant="outline" onClick={() => navigate("/migrations")}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to migrations
      </Button>

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold">{migration.job_name}</h1>
          <p className="mt-2 text-sm text-muted-foreground">Inspection view for a single migration job.</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={migration.status} />
          <div className="flex gap-2">
            {migration.status === "PENDING" && (
              <Button 
                size="sm" 
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
            )}
            {migration.status === "RUNNING" && (
              <Button 
                size="sm" 
                variant="destructive"
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
              >
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            )}
            {migration.status === "FAILED" && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
            <CardDescription>Core metadata stored in the backend.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-3">
              <FolderKanban className="mt-0.5 h-5 w-5 text-primary" />
              <div>
                <p className="text-sm font-semibold">Description</p>
                <p className="text-sm text-muted-foreground">{migration.description || "No description provided."}</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border p-3">
                <p className="text-sm font-semibold">Source database ID</p>
                <p className="mt-1 text-sm text-muted-foreground">{migration.source_database_config_id || "Not set"}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-sm font-semibold">Destination database ID</p>
                <p className="mt-1 text-sm text-muted-foreground">{migration.destination_database_config_id || "Not set"}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Lifecycle</CardTitle>
            <CardDescription>Timing details from the backend model.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-3">
              <CalendarDays className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-foreground">Created</p>
                <p>{formatDate(migration.created_at)}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Database className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-foreground">Updated</p>
                <p>{formatDate(migration.updated_at)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-violet-500" />
              Lambda Execution Status
            </CardTitle>
            <CardDescription>Real-time Lambda migration progress and chunk status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="h-4 w-4 text-violet-500" />
              <span className="text-sm font-medium text-foreground">Architecture: Lambda</span>
            </div>

            {migration.status === "RUNNING" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{migration.progress_percent?.toFixed(1) || 0}%</span>
                </div>
                <ProgressBar value={migration.progress_percent || 0} className="h-2" />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{migration.rows_migrated?.toLocaleString() || 0} rows migrated</span>
                  <span>{migration.total_rows?.toLocaleString() || 0} total rows</span>
                </div>
              </div>
            )}

            {migration.lambda_migration_id && (
              <div className="space-y-3 pt-3 border-t">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">Lambda Migration ID</p>
                    <p className="font-medium text-foreground">{migration.lambda_migration_id}</p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">Lambda Status</p>
                    <p className="font-medium text-foreground capitalize">{migration.lambda_status || "Unknown"}</p>
                  </div>
                </div>

                {migration.chunks_total !== undefined && migration.chunks_total > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-foreground">Chunk Progress</p>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div className="rounded-lg border p-2 text-center">
                        <p className="text-xs text-muted-foreground">Created</p>
                        <p className="font-medium text-blue-600">{migration.chunks_created || 0}</p>
                      </div>
                      <div className="rounded-lg border p-2 text-center">
                        <p className="text-xs text-muted-foreground">Completed</p>
                        <p className="font-medium text-green-600">{migration.chunks_completed || 0}</p>
                      </div>
                      <div className="rounded-lg border p-2 text-center">
                        <p className="text-xs text-muted-foreground">Failed</p>
                        <p className="font-medium text-red-600">{migration.chunks_failed || 0}</p>
                      </div>
                    </div>
                    <ProgressBar 
                      value={migration.chunks_total > 0 ? ((migration.chunks_completed || 0) / migration.chunks_total) * 100 : 0} 
                      className="h-1.5"
                    />
                  </div>
                )}

                {migration.current_stage && (
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-violet-500" />
                    <span className="text-muted-foreground">Current Stage:</span>
                    <span className="font-medium text-foreground capitalize">{migration.current_stage}</span>
                  </div>
                )}
              </div>
            )}

            {migration.status === "PENDING" && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                <span>Click "Start" to begin Lambda migration execution</span>
              </div>
            )}

            {migration.status === "COMPLETED" && (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <CheckCircle2 className="h-4 w-4" />
                <span>Migration completed successfully</span>
              </div>
            )}

            {migration.status === "FAILED" && migration.error_message && (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                <p className="font-medium mb-1">Error</p>
                <p className="text-xs">{migration.error_message}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Migration Logs</CardTitle>
            <CardDescription>Real-time logs from Lambda functions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 mb-4">
              <Terminal className="h-4 w-4 text-primary" />
              <span className="text-sm text-muted-foreground">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <div className="bg-black text-green-400 font-mono text-xs p-4 rounded-lg h-64 overflow-y-auto">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <div key={index} className="border-b border-gray-800 py-1">
                    {log}
                  </div>
                ))
              ) : (
                <div className="text-gray-500">No logs available yet...</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
