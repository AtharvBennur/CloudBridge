import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Activity, ArrowUpRight, CheckCircle2, Cloud, Database, KeyRound, Server, ShieldCheck, Workflow } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { env } from "@/lib/env";
import { getHealth } from "@/services/healthService";

const overviewCards = [
  { label: "Total Migrations", value: "12", change: "+2 this week", icon: Database },
  { label: "Running", value: "3", change: "2 active now", icon: Workflow },
  { label: "Completed", value: "8", change: "98% success", icon: CheckCircle2 },
  { label: "Failed", value: "1", change: "Needs review", icon: Activity },
];

export function DashboardPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  const apiStatus = healthQuery.data?.status === "healthy" ? "Healthy" : "Unavailable";
  const cognitoPrepared = Boolean(env.cognitoRegion && env.cognitoUserPoolId && env.cognitoClientId);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-4 lg:grid-cols-[1.55fr_0.95fr]"
      >
        <div className="rounded-2xl border border-border/70 bg-gradient-to-br from-primary/10 via-background to-background p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <Badge variant="success">Operating</Badge>
            <Badge variant="secondary">Sprint 4</Badge>
          </div>
          <h1 className="mt-4 text-3xl font-semibold leading-tight md:text-4xl">
            CloudBridge is ready for enterprise-ready AWS onboarding workflows.
          </h1>
          <p className="mt-3 max-w-2xl text-base text-muted-foreground">
            This console now provides a polished foundation for migration management, AWS connection onboarding, and future deployment orchestration.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <div className="rounded-xl border bg-background/80 px-3 py-2 text-sm text-muted-foreground">
              Protected routes enabled
            </div>
            <div className="rounded-xl border bg-background/80 px-3 py-2 text-sm text-muted-foreground">
              AWS connection metadata ready
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-border/70 shadow-sm">
          <CardHeader className="bg-muted/40">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>API Health</CardTitle>
                <CardDescription>Live response from GET /health</CardDescription>
              </div>
              <div className="rounded-full bg-emerald-500/10 p-2 text-emerald-600">
                <Activity className="h-5 w-5" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-5">
            {healthQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-8 w-28" />
                <Skeleton className="h-4 w-40" />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-3xl font-semibold">{apiStatus}</p>
                    <p className="text-sm text-muted-foreground">{env.apiBaseUrl}</p>
                  </div>
                  <Badge variant={apiStatus === "Healthy" ? "success" : "warning"}>{apiStatus}</Badge>
                </div>
                <div className="rounded-xl border bg-muted/30 p-4 text-sm text-muted-foreground">
                  The backend service is available for the frontend and supports the migration and AWS onboarding flows.
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {overviewCards.map((item, index) => {
          const Icon = item.icon;
          return (
            <motion.div key={item.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: index * 0.06 }}>
              <Card className="border-border/70 shadow-sm">
                <CardContent className="pt-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{item.label}</p>
                      <p className="mt-2 text-3xl font-semibold">{item.value}</p>
                    </div>
                    <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                    <ArrowUpRight className="h-4 w-4 text-emerald-600" />
                    {item.change}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <Server className="mb-2 h-5 w-5 text-primary" />
            <CardTitle>Backend foundation</CardTitle>
            <CardDescription>Flask blueprints, services, and structured errors keep the core stable.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>SQLAlchemy and Alembic are ready for future schema ownership.</p>
            <p>Gunicorn and Docker support production-style execution.</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <ShieldCheck className="mb-2 h-5 w-5 text-primary" />
            <CardTitle>Authentication readiness</CardTitle>
            <CardDescription>Protected routes and session-based auth are ready for Cognito.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Your dashboard remains guarded while the identity backbone is prepared.</p>
            <p>Cognito environment status: {cognitoPrepared ? "configured" : "waiting for values"}.</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <Workflow className="mb-2 h-5 w-5 text-primary" />
            <CardTitle>AWS migration workflow</CardTitle>
            <CardDescription>The console now includes dedicated AWS connection onboarding.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Create, manage, and inspect cloud connection metadata from the console.</p>
            <p>Future STS and deployment steps can extend this surface cleanly.</p>
          </CardContent>
        </Card>
      </section>

      <section className="rounded-2xl border border-border/70 bg-card/80 p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-base font-semibold">Security posture</p>
            <p className="text-sm text-muted-foreground">
              Authentication remains local until Cognito is deliberately wired in, but the project is already structured for enterprise-grade expansion.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground">
            <KeyRound className="h-4 w-4" />
            Cognito-ready
          </div>
        </div>
      </section>
    </div>
  );
}
