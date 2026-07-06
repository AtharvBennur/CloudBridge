/*
Purpose:
This file displays a single migration job in detail.

Why:
Users need a high-level view of metadata and status for one migration job.

Architecture:
Protected App Shell
↓
Migration Detail Page
↓
Migration Service
*/

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Database, CalendarDays, FolderKanban } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { StatusBadge } from "@/components/migrations/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { migrationService } from "@/services/migrationService";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export function MigrationDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const migrationId = Number(id);

  const migrationQuery = useQuery({
    queryKey: ["migration", migrationId],
    queryFn: () => migrationService.getById(migrationId),
    enabled: Number.isFinite(migrationId),
  });

  if (migrationQuery.isLoading) {
    return <div className="rounded-lg border border-dashed p-8 text-sm text-muted-foreground">Loading migration details…</div>;
  }

  if (migrationQuery.isError || !migrationQuery.data) {
    return (
      <div className="space-y-4">
        <Button variant="outline" onClick={() => navigate("/migrations")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to migrations
        </Button>
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {migrationQuery.error instanceof Error ? migrationQuery.error.message : "Unable to load migration job."}
        </div>
      </div>
    );
  }

  const migration = migrationQuery.data;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Button variant="outline" onClick={() => navigate("/migrations")}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to migrations
      </Button>

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold">{migration.job_name}</h1>
          <p className="mt-2 text-sm text-muted-foreground">Inspection view for a single migration job.</p>
        </div>
        <StatusBadge status={migration.status} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
            <CardDescription>Core metadata stored in the backend.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-3">
              <FolderKanban className="mt-0.5 h-5 w-5 text-primary" />
              <div>
                <p className="text-sm font-semibold">Description</p>
                <p className="text-sm text-muted-foreground">{migration.description || "No description provided."}</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border p-3">
                <p className="text-sm font-semibold">Source database</p>
                <p className="mt-1 text-sm text-muted-foreground">{migration.source_database}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-sm font-semibold">Destination database</p>
                <p className="mt-1 text-sm text-muted-foreground">{migration.destination_database}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Lifecycle</CardTitle>
            <CardDescription>Timing details from the backend model.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-3">
              <CalendarDays className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-foreground">Created</p>
                <p>{formatDate(migration.created_at)}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Database className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-foreground">Updated</p>
                <p>{formatDate(migration.updated_at)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
