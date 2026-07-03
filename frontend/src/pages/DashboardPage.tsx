import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Activity, CheckCircle2, Database, KeyRound, Server, ShieldCheck } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { env } from "@/lib/env";
import { getHealth } from "@/services/healthService";

const readinessItems = [
  { label: "Application shell", status: "Ready" },
  { label: "Protected routing", status: "Ready" },
  { label: "Theme system", status: "Ready" },
  { label: "API client", status: "Ready" },
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
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-4 lg:grid-cols-[1.5fr_1fr]"
      >
        <div className="rounded-lg border bg-card p-6 shadow-soft">
          <p className="mb-3 text-sm font-semibold uppercase text-primary">CloudBridge Console</p>
          <h1 className="text-3xl font-semibold leading-tight md:text-4xl">
            Sprint 1 foundation is ready for product work.
          </h1>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            The dashboard verifies frontend routing, auth boundaries, theme behavior, and backend
            health without introducing migration workflows or AWS orchestration.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>API Health</CardTitle>
            <CardDescription>Live response from `GET /health`.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-lg bg-secondary text-secondary-foreground">
                <Activity className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-semibold">{healthQuery.isLoading ? "Checking" : apiStatus}</p>
                <p className="text-sm text-muted-foreground">{env.apiBaseUrl}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {readinessItems.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.06 }}
          >
            <Card>
              <CardContent className="flex items-center justify-between pt-5">
                <div>
                  <p className="text-sm text-muted-foreground">{item.label}</p>
                  <p className="mt-1 text-xl font-semibold">{item.status}</p>
                </div>
                <CheckCircle2 className="h-6 w-6 text-primary" />
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <Server className="mb-2 h-5 w-5 text-primary" />
            <CardTitle>Backend</CardTitle>
            <CardDescription>Flask app factory with blueprints and centralized errors.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>SQLAlchemy and Alembic are wired for future schema ownership.</p>
            <p>Gunicorn and Docker support production-style execution.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <ShieldCheck className="mb-2 h-5 w-5 text-primary" />
            <CardTitle>Authentication</CardTitle>
            <CardDescription>Context and service boundaries are ready for Cognito.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Protected routes guard dashboard access.</p>
            <p>Cognito environment status: {cognitoPrepared ? "configured" : "waiting for values"}.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Database className="mb-2 h-5 w-5 text-primary" />
            <CardTitle>Data Layer</CardTitle>
            <CardDescription>Persistence primitives exist without product workflows.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>No migration feature pages or AWS orchestration are present.</p>
            <p>Configuration is environment-driven with no hardcoded secrets.</p>
          </CardContent>
        </Card>
      </section>

      <section className="rounded-lg border bg-card p-5 shadow-soft">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-base font-semibold">Security posture</p>
            <p className="text-sm text-muted-foreground">
              Sprint 1 keeps auth local to the browser session until Cognito is deliberately configured.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-md bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground">
            <KeyRound className="h-4 w-4" />
            Cognito-ready
          </div>
        </div>
      </section>
    </div>
  );
}
