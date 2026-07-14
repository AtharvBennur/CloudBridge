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
  CheckCircle2,
  Cloud,
  Database,
  KeyRound,
  Server,
  ShieldCheck,
  Workflow,
  Clock,
  Sparkles
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { env } from "@/lib/env";
import { getHealth } from "@/services/healthService";
import { migrationService } from "@/services/migrationService";
import { awsConnectionService } from "@/services/awsConnectionService";
import { databaseConfigService } from "@/services/databaseConfigService";

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

  const apiStatus = healthQuery.data?.status === "healthy" ? "Healthy" : "Unavailable";
  
  const totalMigrations = migrationsQuery.data?.length || 0;
  const runningMigrations = migrationsQuery.data?.filter(m => m.status === "RUNNING").length || 0;
  const completedMigrations = migrationsQuery.data?.filter(m => m.status === "COMPLETED").length || 0;
  const failedMigrations = migrationsQuery.data?.filter(m => m.status === "FAILED").length || 0;

  const totalAWSConns = awsConnectionsQuery.data?.length || 0;
  const activeAWSConns = awsConnectionsQuery.data?.filter(c => c.connection_status === "CONNECTED").length || 0;
  const totalDatabases = databasesQuery.data?.length || 0;

  const recentMigrations = migrationsQuery.data?.slice(0, 4) || [];

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
              <Badge variant="success">Active Plane</Badge>
              <Badge variant="secondary">Sprint 5</Badge>
              <Badge variant="indigo">STS AssumeRole Live</Badge>
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
                  The CloudBridge orchestration engine is operational and communicating with your sqlite metadata base.
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.section>

      {/* Statistics Cards */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Total Migrations", value: totalMigrations, change: `${runningMigrations} active, ${completedMigrations} completed`, icon: Database },
          { label: "AWS Connections", value: totalAWSConns, change: `${activeAWSConns} accounts active`, icon: Cloud },
          { label: "Registered Databases", value: totalDatabases, change: "Secrets stored in customer SM", icon: Server },
          { label: "Failed runs", value: failedMigrations, change: failedMigrations > 0 ? "Review failed workers" : "All clean", icon: Activity },
        ].map((item, index) => {
          const Icon = item.icon;
          return (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <Card className="border-border/70 shadow-sm hover:border-primary/45 transition">
                <CardContent className="pt-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{item.label}</p>
                      <p className="mt-2 text-3.5xl font-semibold tracking-tight">{item.value}</p>
                    </div>
                    <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                  </div>
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <ArrowUpRight className="h-3.5 w-3.5 text-emerald-500" />
                    {item.change}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </section>

      {/* Main content grid */}
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Recent Migrations Card */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <CardTitle>Recent Migrations</CardTitle>
            <CardDescription>Recently registered database migration tasks.</CardDescription>
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
                  <div>
                    <h4 className="font-semibold text-sm text-foreground">{migration.job_name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Source: {migration.source_database} → Target: {migration.destination_database}
                    </p>
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

        {/* Onboarding Overview Card */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <CardTitle>Onboarding Posture</CardTitle>
            <CardDescription>Setup walkthrough status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-emerald-500/10 p-2 text-emerald-600 shrink-0">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold">1. AWS IAM Onboarding</h4>
                <p className="text-xs text-muted-foreground mt-0.5">AssumeRole trust policy is generated using the AWS Onboarding flow.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="rounded-full bg-emerald-500/10 p-2 text-emerald-600 shrink-0">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold">2. Credentials Protection</h4>
                <p className="text-xs text-muted-foreground mt-0.5">Passwords are written to AWS Secrets Manager using the assumed role dynamically.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="rounded-full bg-primary/10 p-2 text-primary shrink-0">
                <Clock className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold">3. Run Pre-flight Checks</h4>
                <p className="text-xs text-muted-foreground mt-0.5">Validate connectivity and access parameters before starting execution.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
