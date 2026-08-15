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

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Database, CalendarDays, FolderKanban, Play, Pause, RotateCcw, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { StatusBadge } from "@/components/migrations/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { migrationService } from "@/services/migrationService";
import { useToast } from "@/components/ui/toast";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export function MigrationDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const migrationId = Number(id);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const migrationQuery = useQuery({
    queryKey: ["migration", migrationId],
    queryFn: () => migrationService.getById(migrationId),
    enabled: Number.isFinite(migrationId),
  });

  const startMutation = useMutation({
    mutationFn: () => migrationService.start(migrationId, migrationQuery.data?.aws_connection_id ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration started", description: "Migration is now running on ECS", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to start migration", description: error.message, variant: "destructive" });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => migrationService.pause(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration paused", description: "Migration has been paused", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to pause migration", description: error.message, variant: "destructive" });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => migrationService.resume(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration resumed", description: "Migration has been resumed", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to resume migration", description: error.message, variant: "destructive" });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => migrationService.cancel(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration cancelled", description: "Migration has been cancelled", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to cancel migration", description: error.message, variant: "destructive" });
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => migrationService.retry(migrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      toast({ title: "Migration retry initiated", description: "Migration will be retried", variant: "success" });
    },
    onError: (error: any) => {
      toast({ title: "Failed to retry migration", description: error.message, variant: "destructive" });
    },
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
        <div className="flex items-center gap-3">
          <StatusBadge status={migration.status} />
          <div className="flex gap-2">
            {migration.status === "PENDING" && (
              <Button 
                size="sm" 
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
            )}
            {migration.status === "RUNNING" && (
              <>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => pauseMutation.mutate()}
                  disabled={pauseMutation.isPending}
                >
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
                <Button 
                  size="sm" 
                  variant="destructive"
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                >
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </>
            )}
            {migration.status === "PAUSED" && (
              <Button 
                size="sm" 
                onClick={() => resumeMutation.mutate()}
                disabled={resumeMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Resume
              </Button>
            )}
            {migration.status === "FAILED" && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            )}
          </div>
        </div>
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
                <p className="text-sm font-semibold">Source database ID</p>
                <p className="mt-1 text-sm text-muted-foreground">{migration.source_database_config_id || "Not set"}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-sm font-semibold">Destination database ID</p>
                <p className="mt-1 text-sm text-muted-foreground">{migration.destination_database_config_id || "Not set"}</p>
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
