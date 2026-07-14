import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Play, Pause, Square, Clock, Database, Activity, Zap, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function CDCPage() {
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
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Clock className="mr-2 h-4 w-4" />
              Schedule
            </Button>
            <Button size="sm">
              <Play className="mr-2 h-4 w-4" />
              Start All
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
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-sm font-medium">Active Streams</span>
              </div>
              <span className="text-2xl font-semibold">3</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Events/sec</span>
              </div>
              <span className="text-2xl font-semibold">1,247</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Avg Lag</span>
              </div>
              <span className="text-2xl font-semibold text-emerald-600">0.3s</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Event Processing</CardTitle>
            <CardDescription>CDC change event statistics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total Events</span>
              <span className="text-2xl font-semibold">2.4M</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Processed</span>
              <span className="text-2xl font-semibold text-emerald-600">2.3M</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Failed</span>
              <span className="text-2xl font-semibold text-red-600">127</span>
            </div>
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
                <span className="text-sm text-muted-foreground">Active Slots</span>
              </div>
              <span className="text-2xl font-semibold">3</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">WAL Retention</span>
              <span className="text-2xl font-semibold">24h</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Disk Usage</span>
              <span className="text-2xl font-semibold">12.4 GB</span>
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
            {[
              { name: "Production to DR", status: "RUNNING", lag: "0.2s", events: "847/sec" },
              { name: "Analytics to Warehouse", status: "RUNNING", lag: "0.5s", events: "312/sec" },
              { name: "Legacy to Cloud", status: "PAUSED", lag: "N/A", events: "0/sec" },
            ].map((stream, index) => (
              <div key={index} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Database className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{stream.name}</h4>
                    <p className="text-sm text-muted-foreground">PostgreSQL WAL streaming</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Lag</p>
                    <p className="text-sm font-medium">{stream.lag}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Events</p>
                    <p className="text-sm font-medium">{stream.events}</p>
                  </div>
                  <Badge variant={stream.status === "RUNNING" ? "success" : "warning"}>
                    {stream.status}
                  </Badge>
                  <div className="flex gap-2">
                    {stream.status === "RUNNING" ? (
                      <Button variant="ghost" size="icon">
                        <Pause className="h-4 w-4" />
                      </Button>
                    ) : (
                      <Button variant="ghost" size="icon">
                        <Play className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon">
                      <Square className="h-4 w-4" />
                    </Button>
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
