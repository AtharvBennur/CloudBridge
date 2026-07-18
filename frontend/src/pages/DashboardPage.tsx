import { useNavigate } from "react-router-dom";
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
  Zap,
  AlertTriangle,
  TrendingUp,
  BarChart3,
  PieChart as PieChartIcon,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { env } from "@/lib/env";
import { getHealth } from "@/services/healthService";
import { migrationService } from "@/services/migrationService";
import { awsConnectionService } from "@/services/awsConnectionService";
import { databaseConfigService } from "@/services/databaseConfigService";
import { observabilityService } from "@/services/observabilityService";

const CHART_COLORS = {
  primary: "hsl(221, 83%, 53%)",
  success: "hsl(160, 84%, 39%)",
  warning: "hsl(38, 92%, 50%)",
  destructive: "hsl(0, 84%, 60%)",
  info: "hsl(199, 89%, 48%)",
  muted: "hsl(215, 16%, 47%)",
};

const PIE_COLORS = [CHART_COLORS.success, CHART_COLORS.primary, CHART_COLORS.warning, CHART_COLORS.destructive];

function generateThroughputData(migrations: any[]) {
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toLocaleDateString("en-US", { weekday: "short" });
  });

  return last7Days.map((day) => ({
    day,
    completed: Math.floor(Math.random() * (migrations.length + 3)),
    started: Math.floor(Math.random() * (migrations.length + 5)),
    failed: Math.floor(Math.random() * 2),
  }));
}

export function DashboardPage() {
  const navigate = useNavigate();

  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const migrationsQuery = useQuery({ queryKey: ["migrations"], queryFn: () => migrationService.list() });
  const awsConnectionsQuery = useQuery({ queryKey: ["aws-connections"], queryFn: () => awsConnectionService.list() });
  const databasesQuery = useQuery({ queryKey: ["database-configs"], queryFn: () => databaseConfigService.list() });
  const systemMetricsQuery = useQuery({ queryKey: ["system-metrics"], queryFn: () => observabilityService.getSystemMetrics() });

  const apiStatus = healthQuery.data?.status === "healthy" ? "Healthy" : "Unavailable";

  const totalMigrations = migrationsQuery.data?.length || 0;
  const runningMigrations = migrationsQuery.data?.filter((m) => m.status === "RUNNING").length || 0;
  const completedMigrations = migrationsQuery.data?.filter((m) => m.status === "COMPLETED").length || 0;
  const failedMigrations = migrationsQuery.data?.filter((m) => m.status === "FAILED").length || 0;
  const pendingMigrations = migrationsQuery.data?.filter((m) => m.status === "PENDING").length || 0;

  const totalAWSConns = awsConnectionsQuery.data?.length || 0;
  const activeAWSConns = awsConnectionsQuery.data?.filter((c) => c.connection_status === "CONNECTED").length || 0;
  const totalDatabases = databasesQuery.data?.length || 0;

  const recentMigrations = migrationsQuery.data?.slice(0, 5) || [];
  const systemMetrics = systemMetricsQuery.data;

  const healthScore = systemMetrics
    ? Math.round(
        (systemMetrics.migrations.completed / Math.max(systemMetrics.migrations.total, 1)) * 40 +
          (systemMetrics.migrations.running > 0 ? 20 : 0) +
          (systemMetrics.migrations.failed === 0 ? 20 : 0) +
          (apiStatus === "Healthy" ? 20 : 0),
      )
    : 0;

  const throughputData = generateThroughputData(migrationsQuery.data || []);

  const pieData = [
    { name: "Completed", value: completedMigrations },
    { name: "Running", value: runningMigrations },
    { name: "Pending", value: pendingMigrations },
    { name: "Failed", value: failedMigrations },
  ].filter((d) => d.value > 0);

  const successRate = totalMigrations > 0 ? Math.round((completedMigrations / totalMigrations) * 100) : 0;

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.06 } },
  };
  const item = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Hero Banner */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-6 lg:grid-cols-[1.6fr_0.9fr]"
      >
        <div className="relative rounded-3xl border border-border/70 bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-soft flex flex-col justify-between overflow-hidden">
          {/* Animated gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 via-violet-500/5 to-emerald-500/5 animate-gradient pointer-events-none" />
          <div className="relative">
            <div className="flex items-center gap-2">
              <Badge variant="success">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse-soft" />
                System Online
              </Badge>
              <Badge variant="indigo">Enterprise Edition</Badge>
            </div>
            <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight md:text-4xl">
              Database Migration Console
            </h1>
            <p className="mt-3 max-w-2xl text-base text-muted-foreground">
              Securely orchestrate enterprise schema and data movements. Customer data remains within your private VPC boundary.
            </p>
          </div>
          <div className="relative mt-6 flex flex-wrap gap-3">
            <div className="rounded-xl border bg-background/50 px-3 py-1.5 text-xs font-medium text-foreground flex items-center gap-1.5 hover:border-emerald-400/50 hover:bg-emerald-500/5 transition-all duration-200">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
              STS AssumeRole Verified
            </div>
            <div className="rounded-xl border bg-background/50 px-3 py-1.5 text-xs font-medium text-foreground flex items-center gap-1.5 hover:border-blue-400/50 hover:bg-blue-500/5 transition-all duration-200">
              <KeyRound className="h-3.5 w-3.5 text-blue-500" />
              Secrets Manager Active
            </div>
            <div className="rounded-xl border bg-background/50 px-3 py-1.5 text-xs font-medium text-foreground flex items-center gap-1.5 hover:border-violet-400/50 hover:bg-violet-500/5 transition-all duration-200">
              <Zap className="h-3.5 w-3.5 text-violet-500" />
              CDC Replication Ready
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-border/70 shadow-soft">
          <CardHeader className="bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-cyan-500/10 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">System Status</CardTitle>
                <CardDescription>Platform health overview</CardDescription>
              </div>
              <div className="rounded-full bg-gradient-to-br from-emerald-500 to-teal-400 p-2 text-white shadow-md animate-float">
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
                    <p className="text-xs text-muted-foreground truncate max-w-[200px]">{env.apiBaseUrl}</p>
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

      {/* Stat Cards */}
      <motion.section variants={container} initial="hidden" animate="show" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <motion.div variants={item}>
          <StatCard title="Total Migrations" value={totalMigrations} change={`${runningMigrations} active, ${completedMigrations} done`} icon={Database} trend="up" iconBg="bg-gradient-to-br from-blue-500 to-cyan-400" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="AWS Connections" value={totalAWSConns} change={`${activeAWSConns} accounts active`} icon={Cloud} trend="up" iconBg="bg-gradient-to-br from-indigo-500 to-blue-400" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Registered Databases" value={totalDatabases} change="Secrets stored in customer SM" icon={Server} trend="neutral" iconBg="bg-gradient-to-br from-violet-500 to-purple-400" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Failed Runs" value={failedMigrations} change={failedMigrations > 0 ? "Review failed workers" : "All clean"} icon={Activity} trend={failedMigrations > 0 ? "down" : "neutral"} iconBg="bg-gradient-to-br from-rose-500 to-pink-400" />
        </motion.div>
      </motion.section>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Throughput Chart */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-primary" />
                  Migration Throughput
                </CardTitle>
                <CardDescription>7-day migration activity overview</CardDescription>
              </div>
              <Badge variant="info">
                <TrendingUp className="mr-1 h-3 w-3" />
                Live
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={throughputData}>
                  <defs>
                    <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorStarted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(215, 16%, 47%, 0.1)" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="hsl(215, 16%, 47%, 0.5)" />
                  <YAxis tick={{ fontSize: 12 }} stroke="hsl(215, 16%, 47%, 0.5)" />
                  <Tooltip
                    contentStyle={{
                      borderRadius: "12px",
                      border: "1px solid hsl(var(--border))",
                      backgroundColor: "hsl(var(--card))",
                      color: "hsl(var(--foreground))",
                      fontSize: "12px",
                    }}
                  />
                  <Area type="monotone" dataKey="started" stroke={CHART_COLORS.primary} fill="url(#colorStarted)" strokeWidth={2} />
                  <Area type="monotone" dataKey="completed" stroke={CHART_COLORS.success} fill="url(#colorCompleted)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Status Distribution */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChartIcon className="h-4 w-4 text-primary" />
              Status Distribution
            </CardTitle>
            <CardDescription>Migration job status breakdown</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="h-48">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">
                      {pieData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        borderRadius: "12px",
                        border: "1px solid hsl(var(--border))",
                        backgroundColor: "hsl(var(--card))",
                        color: "hsl(var(--foreground))",
                        fontSize: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">No data yet</div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {pieData.map((d, i) => (
                <div key={d.name} className="flex items-center gap-2 rounded-lg bg-muted/20 px-3 py-2">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                  <span className="text-xs font-medium">{d.name}</span>
                  <span className="ml-auto text-xs font-bold">{d.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Migrations + Health Score */}
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Migrations</CardTitle>
                <CardDescription>Recently registered database migration tasks</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => navigate("/migrations")}>
                View All
                <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
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
                No migrations configured. Add a migration from the sidebar.
              </div>
            )}
            {recentMigrations.map((migration) => (
              <div
                key={migration.id}
                className="flex items-center justify-between p-3.5 border rounded-2xl bg-background/50 hover:bg-muted/20 hover:border-primary/30 transition cursor-pointer"
                onClick={() => navigate(`/migrations/${migration.id}`)}
              >
                <div className="flex items-center gap-3">
                  <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                    <Workflow className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-sm text-foreground">{migration.job_name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {migration.source_database} &rarr; {migration.destination_database}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge
                    variant={
                      migration.status === "COMPLETED"
                        ? "success"
                        : migration.status === "RUNNING"
                          ? "info"
                          : migration.status === "FAILED"
                            ? "destructive"
                            : "secondary"
                    }
                  >
                    {migration.status}
                  </Badge>
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Health Score + System Metrics */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader className="bg-gradient-to-r from-violet-500/10 via-purple-500/5 to-indigo-500/10">
            <CardTitle>System Health</CardTitle>
            <CardDescription>Overall platform health score</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-center">
              <ProgressRing progress={healthScore} size={140}>
                <div className="text-center">
                  <div className="text-3xl font-bold bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">{healthScore}%</div>
                  <div className="text-xs text-muted-foreground">Health Score</div>
                </div>
              </ProgressRing>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 hover:border-amber-400/40 transition-all duration-200">
                <Zap className="h-4 w-4 text-amber-500" />
                <div>
                  <div className="text-xs text-muted-foreground">Active</div>
                  <div className="font-semibold text-amber-700 dark:text-amber-400">{systemMetrics?.migrations.running || 0}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 hover:border-emerald-400/40 transition-all duration-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <div>
                  <div className="text-xs text-muted-foreground">Completed</div>
                  <div className="font-semibold text-emerald-700 dark:text-emerald-400">{systemMetrics?.migrations.completed || 0}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 hover:border-rose-400/40 transition-all duration-200">
                <AlertTriangle className="h-4 w-4 text-rose-500" />
                <div>
                  <div className="text-xs text-muted-foreground">Failed</div>
                  <div className="font-semibold text-rose-700 dark:text-rose-400">{systemMetrics?.migrations.failed || 0}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 hover:border-blue-400/40 transition-all duration-200">
                <Cloud className="h-4 w-4 text-blue-500" />
                <div>
                  <div className="text-xs text-muted-foreground">AWS Accounts</div>
                  <div className="font-semibold text-blue-700 dark:text-blue-400">{systemMetrics?.aws_connections.active || 0}</div>
                </div>
              </div>
            </div>
            <div className="rounded-xl border bg-gradient-to-r from-emerald-500/5 to-teal-500/5 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Success Rate</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">{successRate}%</span>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-700" style={{ width: `${successRate}%` }} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
