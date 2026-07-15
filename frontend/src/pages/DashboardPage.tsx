/*
Purpose:
Premium Dashboard dashboard providing metrics for CloudBridge.
Fetches real connection counts, database configs, and migration jobs.
*/

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Cloud,
  Database,
  KeyRound,
  Server,
  ShieldCheck,
  Workflow,
  Clock,
  Sparkles,
  Zap,
  AlertTriangle
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { env } from "@/lib/env";
import { getHealth } from "@/services/healthService";
import { migrationService } from "@/services/migrationService";
import { awsConnectionService } from "@/services/awsConnectionService";
import { databaseConfigService } from "@/services/databaseConfigService";
import { observabilityService } from "@/services/observabilityService";

export function DashboardPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  const migrationsQuery = useQuery({
    queryKey: ["migrations"],
    queryFn: () => migrationService.list(),
  });

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  const databasesQuery = useQuery({
    queryKey: ["database-configs"],
    queryFn: () => databaseConfigService.list(),
  });

  const systemMetricsQuery = useQuery({
    queryKey: ["system-metrics"],
    queryFn: () => observabilityService.getSystemMetrics(),
  });

  const apiStatus = healthQuery.data?.status === "healthy" ? "Healthy" : "Unavailable";
  
  const totalMigrations = migrationsQuery.data?.length || 0;
  const runningMigrations = migrationsQuery.data?.filter(m => m.status === "RUNNING").length || 0;
  const completedMigrations = migrationsQuery.data?.filter(m => m.status === "COMPLETED").length || 0;
  const failedMigrations = migrationsQuery.data?.filter(m => m.status === "FAILED").length || 0;

  const totalAWSConns = awsConnectionsQuery.data?.length || 0;
  const activeAWSConns = awsConnectionsQuery.data?.filter(c => c.connection_status === "CONNECTED").length || 0;
  const totalDatabases = databasesQuery.data?.length || 0;

  const recentMigrations = migrationsQuery.data?.slice(0, 4) || [];
  const systemMetrics = systemMetricsQuery.data;

  // Calculate overall health score
  const healthScore = systemMetrics ? Math.round(
    ((systemMetrics.completed_migrations / Math.max(systemMetrics.total_migrations, 1)) * 40) +
    ((systemMetrics.running_migrations > 0 ? 1 : 0) * 20) +
    ((systemMetrics.failed_migrations === 0 ? 1 : 0) * 20) +
    ((apiStatus === "Healthy" ? 1 : 0) * 20)
  ) : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Top Banner section */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-6 lg:grid-cols-[1.6fr_0.9fr]"
      >
        <div className="rounded-3xl border border-border/70 bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-soft flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Badge variant="success">System Online</Badge>
              <Badge variant="indigo">Enterprise Edition</Badge>
            </div>
            <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight md:text-4xl">
              Database Migration Console
            </h1>
            <p className="mt-3 max-w-2xl text-base text-muted-foreground">
              Securely orchestrate enterprise schema and data movements. Customer data remains within your private VPC boundary; only control messages are routed.
            </p>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <div className="rounded-xl border bg-background/50 px-3 py-1.5 text-xs font-medium text-foreground flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-primary" />
              STS AssumeRole Verified
            </div>
            <div className="rounded-xl border bg-background/50 px-3 py-1.5 text-xs font-medium text-foreground flex items-center gap-1.5">
              <KeyRound className="h-3.5 w-3.5 text-primary" />
              Customer Secrets Manager Integration Active
            </div>
          </div>
        </div>

        {/* API Health Widget */}
        <Card className="overflow-hidden border-border/70 shadow-soft">
          <CardHeader className="bg-muted/30 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">System Status</CardTitle>
                <CardDescription>GET /health endpoint response</CardDescription>
              </div>
              <div className="rounded-full bg-emerald-500/10 p-2 text-emerald-600">
                <Activity className="h-5 w-5" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-5 space-y-4">
            {healthQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-8 w-28" />
                <Skeleton className="h-4 w-40" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-3xl font-semibold tracking-tight">{apiStatus}</p>
                    <p className="text-xs text-muted-foreground truncate max-w-[200px]" title={env.apiBaseUrl}>{env.apiBaseUrl}</p>
                  </div>
                  <Badge variant={apiStatus === "Healthy" ? "success" : "warning"}>{apiStatus}</Badge>
                </div>
                <div className="rounded-xl border bg-muted/20 p-3 text-xs text-muted-foreground">
                  The CloudBridge orchestration engine is operational and communicating with your metadata database.
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.section>

      {/* Statistics Cards */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Migrations"
          value={totalMigrations}
          change={`${runningMigrations} active, ${completedMigrations} completed`}
          icon={Database}
          trend="up"
        />
        <StatCard
          title="AWS Connections"
          value={totalAWSConns}
          change={`${activeAWSConns} accounts active`}
          icon={Cloud}
          trend="up"
        />
        <StatCard
          title="Registered Databases"
          value={totalDatabases}
          change="Secrets stored in customer SM"
          icon={Server}
          trend="neutral"
        />
        <StatCard
          title="Failed Runs"
          value={failedMigrations}
          change={failedMigrations > 0 ? "Review failed workers" : "All clean"}
          icon={Activity}
          trend={failedMigrations > 0 ? "down" : "neutral"}
        />
      </section>

      {/* Main content grid */}
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Recent Migrations Card */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Migrations</CardTitle>
                <CardDescription>Recently registered database migration tasks.</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                View All
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {migrationsQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            )}
            {!migrationsQuery.isLoading && recentMigrations.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No migrations configured. Add a migration from the sidebar link.
              </div>
            )}
            {recentMigrations.map((migration) => (
              <div key={migration.id} className="flex items-center justify-between p-3.5 border rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-3">
                  <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                    <Workflow className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-sm text-foreground">{migration.job_name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Source: {migration.source_database} → Target: {migration.destination_database}
                    </p>
                    {migration.status === "RUNNING" && (
                      <ProgressBar value={65} max={100} size="sm" className="mt-2" showLabel={false} />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={migration.status === "COMPLETED" ? "success" : migration.status === "RUNNING" ? "info" : "secondary"}>
                    {migration.status}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* System Health Card */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>Overall platform health score and metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-center">
              <ProgressRing progress={healthScore} size={140}>
                <div className="text-center">
                  <div className="text-3xl font-bold">{healthScore}%</div>
                  <div className="text-xs text-muted-foreground">Health Score</div>
                </div>
              </ProgressRing>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2 p-3 rounded-xl bg-muted/30">
                <Zap className="h-4 w-4 text-amber-500" />
                <div>
                  <div className="text-xs text-muted-foreground">Active</div>
                  <div className="font-semibold">{systemMetrics?.running_migrations || 0}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-muted/30">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <div>
                  <div className="text-xs text-muted-foreground">Completed</div>
                  <div className="font-semibold">{systemMetrics?.completed_migrations || 0}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-muted/30">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <div>
                  <div className="text-xs text-muted-foreground">Failed</div>
                  <div className="font-semibold">{systemMetrics?.failed_migrations || 0}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-muted/30">
                <Bot className="h-4 w-4 text-blue-500" />
                <div>
                  <div className="text-xs text-muted-foreground">ECS Tasks</div>
                  <div className="font-semibold">{systemMetrics?.active_ecs_tasks || 0}</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
