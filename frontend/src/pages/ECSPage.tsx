import { motion } from "framer-motion";
import { Activity, Play, Pause, Square, Server, Clock, CheckCircle2, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ECSPage() {
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
            <div className="text-3xl font-semibold text-emerald-600">8</div>
            <p className="text-xs text-muted-foreground mt-1">Active Fargate tasks</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">3</div>
            <p className="text-xs text-muted-foreground mt-1">Queued for execution</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">1</div>
            <p className="text-xs text-muted-foreground mt-1">Requires attention</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">142</div>
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
            {[
              { name: "migration-prod-dr", status: "RUNNING", cpu: "256", memory: "512", started: "2h 34m", migration: "Production to DR" },
              { name: "migration-analytics", status: "RUNNING", cpu: "512", memory: "1024", started: "1h 12m", migration: "Analytics to Warehouse" },
              { name: "migration-legacy", status: "STOPPED", cpu: "256", memory: "512", started: "45m", migration: "Legacy to Cloud" },
              { name: "migration-test", status: "FAILED", cpu: "256", memory: "512", started: "23m", migration: "Test Migration" },
            ].map((task, index) => (
              <div key={index} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    task.status === "RUNNING" ? "bg-emerald-500/10 text-emerald-600" : 
                    task.status === "STOPPED" ? "bg-gray-500/10 text-gray-600" : 
                    "bg-red-500/10 text-red-600"
                  }`}>
                    <Server className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{task.name}</h4>
                    <p className="text-sm text-muted-foreground">{task.migration}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span>CPU: {task.cpu}</span>
                      <span>Memory: {task.memory}MB</span>
                      <span>Started: {task.started}</span>
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
                        <Button variant="ghost" size="icon">
                          <Pause className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon">
                          <Square className="h-4 w-4" />
                        </Button>
                      </>
                    ) : task.status === "STOPPED" ? (
                      <Button variant="ghost" size="icon">
                        <Play className="h-4 w-4" />
                      </Button>
                    ) : (
                      <Button variant="ghost" size="icon">
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
