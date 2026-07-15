import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Play, Pause, Square, Clock, Database, Activity, Zap, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cdcService } from "@/services/cdcService";
import { migrationService } from "@/services/migrationService";

export function CDCPage() {
  const [selectedMigrationId, setSelectedMigrationId] = useState<number | null>(null);

  const migrationsQuery = useQuery({
    queryKey: ["migrations-list"],
    queryFn: () => migrationService.list(),
  });

  const cdcConfigsQuery = useQuery({
    queryKey: ["cdc-configs", selectedMigrationId],
    queryFn: () => cdcService.getConfig(selectedMigrationId!),
    enabled: !!selectedMigrationId,
  });

  const cdcStatsQuery = useQuery({
    queryKey: ["cdc-stats", selectedMigrationId],
    queryFn: () => cdcService.getStatistics(selectedMigrationId!),
    enabled: !!selectedMigrationId && !!cdcConfigsQuery.data,
  });

  const cdcEventsQuery = useQuery({
    queryKey: ["cdc-events", selectedMigrationId],
    queryFn: () => cdcService.getEvents(selectedMigrationId!, undefined, 50),
    enabled: !!selectedMigrationId && !!cdcConfigsQuery.data,
  });

  const handleStart = async () => {
    if (!selectedMigrationId) return;
    try {
      await cdcService.start(selectedMigrationId);
      cdcConfigsQuery.refetch();
    } catch (error) {
      console.error("Failed to start CDC:", error);
    }
  };

  const handlePause = async () => {
    if (!selectedMigrationId) return;
    try {
      await cdcService.pause(selectedMigrationId);
      cdcConfigsQuery.refetch();
    } catch (error) {
      console.error("Failed to pause CDC:", error);
    }
  };

  const handleStop = async () => {
    if (!selectedMigrationId) return;
    try {
      await cdcService.stop(selectedMigrationId);
      cdcConfigsQuery.refetch();
    } catch (error) {
      console.error("Failed to stop CDC:", error);
    }
  };

  const config = cdcConfigsQuery.data;
  const stats = cdcStatsQuery.data;
  const events = cdcEventsQuery.data || [];

  const migrations = migrationsQuery.data || [];

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 p-3 text-white shadow-lg">
            <Zap className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">CDC Replication</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Real-time Change Data Capture with PostgreSQL WAL streaming and continuous replication.
            </p>
            <div className="mt-4">
              <label htmlFor="cdc-migration-select" className="text-sm font-medium text-muted-foreground mb-1 block">Select Migration</label>
              <select
                id="cdc-migration-select"
                className="h-10 w-full max-w-xs rounded-xl border border-border/70 bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/20"
                value={selectedMigrationId ?? ""}
                onChange={(e) => setSelectedMigrationId(Number(e.target.value) || null)}
              >
                <option value="">Choose a migration...</option>
                {migrations.map((m) => (
                  <option key={m.id} value={m.id}>{m.job_name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handlePause} disabled={!config || config.status !== "RUNNING"}>
              <Pause className="mr-2 h-4 w-4" />
              Pause
            </Button>
            <Button size="sm" onClick={handleStart} disabled={!config || config.status === "RUNNING"}>
              <Play className="mr-2 h-4 w-4" />
              Start
            </Button>
            <Button variant="outline" size="sm" onClick={handleStop} disabled={!config || config.status === "IDLE"}>
              <Square className="mr-2 h-4 w-4" />
              Stop
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Replication Status</CardTitle>
            <CardDescription>Real-time CDC streaming metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {stats ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`h-2 w-2 rounded-full ${config?.status === "RUNNING" ? "bg-emerald-500" : "bg-gray-500"}`} />
                    <span className="text-sm font-medium">Status</span>
                  </div>
                  <Badge variant={config?.status === "RUNNING" ? "success" : "secondary"}>{config?.status || "IDLE"}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Events/sec</span>
                  </div>
                  <span className="text-2xl font-semibold">{stats.events_per_second || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Avg Lag</span>
                  </div>
                  <span className="text-2xl font-semibold text-emerald-600">{stats.avg_lag_seconds?.toFixed(1) || 0}s</span>
                </div>
              </>
            ) : (
              <Skeleton className="h-20 w-full" />
            )}
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Event Processing</CardTitle>
            <CardDescription>CDC change event statistics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {stats ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Total Events</span>
                  <span className="text-2xl font-semibold">{stats.total_events || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Processed</span>
                  <span className="text-2xl font-semibold text-emerald-600">{stats.processed_events || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Failed</span>
                  <span className="text-2xl font-semibold text-red-600">{stats.failed_events || 0}</span>
                </div>
              </>
            ) : (
              <Skeleton className="h-20 w-full" />
            )}
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Replication Slots</CardTitle>
            <CardDescription>PostgreSQL WAL slot status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Replication Slot</span>
              </div>
              <span className="text-sm font-medium">{config?.replication_slot_name || "N/A"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">CDC Mode</span>
              <span className="text-sm font-medium">{config?.cdc_mode || "N/A"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Max Lag</span>
              <span className="text-sm font-medium">{config?.max_lag_seconds || 0}s</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Active Replication Streams</CardTitle>
          <CardDescription>Real-time CDC replication status for all active migrations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {cdcEventsQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!cdcEventsQuery.isLoading && events.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No CDC events recorded yet. Start CDC replication to begin capturing changes.
              </div>
            )}
            {!cdcEventsQuery.isLoading && events.slice(0, 5).map((event, index) => (
              <div key={index} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    event.event_type === "INSERT" ? "bg-emerald-500/10 text-emerald-600" :
                    event.event_type === "UPDATE" ? "bg-blue-500/10 text-blue-600" :
                    "bg-red-500/10 text-red-600"
                  }`}>
                    <Database className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{event.event_type}</h4>
                    <p className="text-sm text-muted-foreground">Table: {event.table_name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={event.status === "PROCESSED" ? "success" : event.status === "FAILED" ? "destructive" : "secondary"}>
                    {event.status}
                  </Badge>
                  <div className="text-xs text-muted-foreground">
                    {new Date(event.created_at).toLocaleString()}
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
