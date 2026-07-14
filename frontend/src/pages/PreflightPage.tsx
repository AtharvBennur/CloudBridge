import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, ClipboardCheck, PlayCircle } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { awsConnectionService } from "@/services/awsConnectionService";
import { databaseConfigService } from "@/services/databaseConfigService";
import { preflightService, type PreflightReport } from "@/services/preflightService";

export function PreflightPage() {
  const [connectionId, setConnectionId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const connections = useQuery({ queryKey: ["aws-connections"], queryFn: awsConnectionService.list });
  const databases = useQuery({ queryKey: ["database-configs"], queryFn: databaseConfigService.list });
  const validation = useMutation({
    mutationFn: () => preflightService.run({
      aws_connection_id: Number(connectionId),
      source_db_id: sourceId ? Number(sourceId) : null,
      destination_db_id: destinationId ? Number(destinationId) : null,
    }),
  });
  const report = validation.data;

  return <div className="mx-auto max-w-6xl space-y-6">
    <section className="rounded-3xl border border-border/70 bg-card/85 p-6 shadow-soft">
      <div className="flex items-start gap-3"><div className="rounded-2xl bg-primary/10 p-3 text-primary"><ClipboardCheck className="h-6 w-6" /></div><div><Badge variant="indigo">Readiness gate</Badge><h1 className="mt-3 text-3xl font-semibold tracking-tight">Pre-flight validation</h1><p className="mt-2 text-sm text-muted-foreground">Verify cross-account access, secrets, permissions, region, and database reachability before a migration starts.</p></div></div>
    </section>
    <Card className="shadow-soft"><CardHeader><CardTitle>Validate migration prerequisites</CardTitle><CardDescription>Choose the infrastructure associated with this migration.</CardDescription></CardHeader><CardContent className="grid gap-4 md:grid-cols-3">
      <Selector label="AWS connection" value={connectionId} onChange={setConnectionId} options={connections.data?.map((item) => ({ value: String(item.id), label: `${item.aws_account_id} · ${item.aws_region}` })) ?? []} />
      <Selector label="Source endpoint" value={sourceId} onChange={setSourceId} options={databases.data?.filter((item) => item.purpose === "SOURCE").map((item) => ({ value: String(item.id), label: item.name })) ?? []} />
      <Selector label="Destination endpoint" value={destinationId} onChange={setDestinationId} options={databases.data?.filter((item) => item.purpose === "DESTINATION").map((item) => ({ value: String(item.id), label: item.name })) ?? []} />
      <div className="md:col-span-3"><Button onClick={() => validation.mutate()} disabled={!connectionId || validation.isPending}><PlayCircle className="mr-2 h-4 w-4" />{validation.isPending ? "Running validation…" : "Run pre-flight"}</Button>{validation.isError ? <p className="mt-3 text-sm text-destructive">{validation.error instanceof Error ? validation.error.message : "Validation failed."}</p> : null}</div>
    </CardContent></Card>
    {report ? <ReadinessReport report={report} /> : null}
  </div>;
}

function Selector({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) {
  return <div className="space-y-2"><Label>{label}</Label><select value={value} onChange={(event) => onChange(event.target.value)} className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"><option value="">Select…</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>;
}

function ReadinessReport({ report }: { report: PreflightReport }) {
  return <Card className="shadow-soft"><CardHeader><div className="flex items-center justify-between"><div><CardTitle>Readiness report</CardTitle><CardDescription>{report.summary}</CardDescription></div><Badge variant={report.status === "READY" ? "success" : "destructive"}>{report.status}</Badge></div></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">{Object.entries(report.checks).map(([name, check]) => <div key={name} className="flex gap-3 rounded-2xl border border-border/70 p-4">{check.status === "PASS" ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" /> : <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />}<div><p className="text-sm font-semibold capitalize">{name.replace(/_/g, " ")}</p><p className="mt-1 text-sm text-muted-foreground">{check.message}</p></div></div>)}</CardContent></Card>;
}
