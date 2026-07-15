import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Activity, Play, Pause, Square, Server, Clock, CheckCircle2, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ecsService } from "@/services/ecsService";
import { migrationService } from "@/services/migrationService";

export function ECSPage() {
  const [selectedMigrationId, setSelectedMigrationId] = useState<number | null>(null);

  const migrationsQuery = useQuery({
    queryKey: ["migrations-list"],
    queryFn: () => migrationService.list(),
  });

  const ecsTasksQuery = useQuery({
    queryKey: ["ecs-tasks", selectedMigrationId],
    queryFn: () => ecsService.listTasks(selectedMigrationId!),
    enabled: !!selectedMigrationId,
  });

  const handleStart = async (taskId: number) => {
    try {
      await ecsService.startTask(taskId);
      ecsTasksQuery.refetch();
    } catch (error) {
      console.error("Failed to start task:", error);
    }
  };

  const handleStop = async (taskId: number) => {
    try {
      await ecsService.stopTask(taskId, "User stopped");
      ecsTasksQuery.refetch();
    } catch (error) {
      console.error("Failed to stop task:", error);
    }
  };

  const handleRetry = async (taskId: number) => {
    try {
      await ecsService.retryTask(taskId);
      ecsTasksQuery.refetch();
    } catch (error) {
      console.error("Failed to retry task:", error);
    }
  };

  const tasks = ecsTasksQuery.data || [];
  const runningTasks = tasks.filter(t => t.status === "RUNNING").length;
  const pendingTasks = tasks.filter(t => t.status === "PENDING").length;
  const failedTasks = tasks.filter(t => t.status === "FAILED").length;
  const completedTasks = tasks.filter(t => t.status === "STOPPED").length;
  const migrations = migrationsQuery.data || [];

  return (
    <div className="mx-auto max-w-7xl space-y-6">
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
            <h1 className="text-3xl font-semibold tracking-tight">ECS/Fargate Tasks</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Manage migration execution on AWS ECS/Fargate with cloud-based task orchestration.
            </p>
            <div className="mt-4">
              <label htmlFor="ecs-migration-select" className="text-sm font-medium text-muted-foreground mb-1 block">Select Migration</label>
              <select
                id="ecs-migration-select"
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
            <Button variant="outline" size="sm">
              <Server className="mr-2 h-4 w-4" />
              Create Task
            </Button>
            <Button size="sm">
              <Play className="mr-2 h-4 w-4" />
              Start All
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Running Tasks</CardTitle>
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
            <p className="text-xs text-muted-foreground mt-1">Total tasks run</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Active ECS Tasks</CardTitle>
          <CardDescription>Real-time status of Fargate migration tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {ecsTasksQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!ecsTasksQuery.isLoading && tasks.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No ECS tasks configured. Create a task to start migration execution on Fargate.
              </div>
            )}
            {!ecsTasksQuery.isLoading && tasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    task.status === "RUNNING" ? "bg-emerald-500/10 text-emerald-600" :
                    task.status === "STOPPED" ? "bg-gray-500/10 text-gray-600" :
                    "bg-red-500/10 text-red-600"
                  }`}>
                    <Server className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{task.task_definition_arn.split('/').pop()}</h4>
                    <p className="text-sm text-muted-foreground">Cluster: {task.cluster_arn.split('/').pop()}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span>CPU: {task.cpu}</span>
                      <span>Memory: {task.memory}MB</span>
                      <span>Type: {task.launch_type}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={task.status === "RUNNING" ? "success" : task.status === "STOPPED" ? "secondary" : "destructive"}>
                    {task.status}
                  </Badge>
                  <div className="flex gap-2">
                    {task.status === "RUNNING" ? (
                      <>
                        <Button variant="ghost" size="icon" onClick={() => handleStop(task.id)}>
                          <Square className="h-4 w-4" />
                        </Button>
                      </>
                    ) : task.status === "FAILED" ? (
                      <Button variant="ghost" size="icon" onClick={() => handleRetry(task.id)}>
                        <Play className="h-4 w-4" />
                      </Button>
                    ) : (
                      <Button variant="ghost" size="icon" onClick={() => handleStart(task.id)}>
                        <Play className="h-4 w-4" />
                      </Button>
                    )}
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
