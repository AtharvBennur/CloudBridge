/*
Purpose:
This file displays the migration-job list view.

Why:
Users need a reliable list page to review and manage their migration work.

Architecture:
Protected App Shell
↓
Migration List Page
↓
Migration Service
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus, Trash2, PencilLine, Eye, DatabaseZap } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDeleteDialog } from "@/components/migrations/ConfirmDeleteDialog";
import { StatusBadge } from "@/components/migrations/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { migrationService } from "@/services/migrationService";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export function MigrationListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedMigrationId, setSelectedMigrationId] = useState<number | null>(null);

  const migrationsQuery = useQuery({
    queryKey: ["migrations"],
    queryFn: () => migrationService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => migrationService.remove(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["migrations"] });
      await queryClient.invalidateQueries({ queryKey: ["migration"] });
      setSelectedMigrationId(null);
    },
  });

  const sortedMigrations = useMemo(() => {
    if (!migrationsQuery.data) {
      return [];
    }

    return [...migrationsQuery.data].sort((left, right) => right.id - left.id);
  }, [migrationsQuery.data]);

  const handleDelete = () => {
    if (selectedMigrationId === null) {
      return;
    }

    deleteMutation.mutate(selectedMigrationId);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/80 p-6 shadow-sm md:flex-row md:items-center md:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <DatabaseZap className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold">Migration jobs</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Review and manage metadata for every workflow in your migration catalog.
            </p>
          </div>
        </div>

        <Button onClick={() => navigate("/migrations/new")}>
          <Plus className="h-4 w-4" />
          New migration
        </Button>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>All migrations</CardTitle>
          <CardDescription>List of jobs created through the backend CRUD API.</CardDescription>
        </CardHeader>
        <CardContent>
          {migrationsQuery.isLoading ? (
            <div className="rounded-2xl border border-dashed p-8 text-sm text-muted-foreground">
              Loading migration jobs…
            </div>
          ) : null}

          {migrationsQuery.isError ? (
            <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
              {migrationsQuery.error instanceof Error
                ? migrationsQuery.error.message
                : "Unable to load migration jobs."}
            </div>
          ) : null}

          {!migrationsQuery.isLoading && !migrationsQuery.isError && sortedMigrations.length === 0 ? (
            <div className="rounded-2xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              No migration jobs yet. Create the first one to get started.
            </div>
          ) : null}

          {!migrationsQuery.isLoading && !migrationsQuery.isError && sortedMigrations.length > 0 ? (
            <div className="overflow-hidden rounded-2xl border border-border/70">
              <table className="min-w-full divide-y divide-border text-sm">
                <thead className="bg-muted/70 text-left">
                  <tr>
                    <th className="px-4 py-3 font-medium">Job name</th>
                    <th className="px-4 py-3 font-medium">Source</th>
                    <th className="px-4 py-3 font-medium">Destination</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Created</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-background/80">
                  {sortedMigrations.map((migration) => (
                    <tr key={migration.id} className="align-middle">
                      <td className="px-4 py-3 font-medium">{migration.job_name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{migration.source_database}</td>
                      <td className="px-4 py-3 text-muted-foreground">{migration.destination_database}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={migration.status} />
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{formatDate(migration.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/migrations/${migration.id}`)}>
                            <Eye className="mr-2 h-4 w-4" />
                            View
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/migrations/${migration.id}/edit`)}>
                            <PencilLine className="mr-2 h-4 w-4" />
                            Edit
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setSelectedMigrationId(migration.id)}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <ConfirmDeleteDialog
        open={selectedMigrationId !== null}
        title="Delete migration job"
        description="This action will remove the migration job from the backend catalog."
        isDeleting={deleteMutation.isPending}
        onCancel={() => setSelectedMigrationId(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
