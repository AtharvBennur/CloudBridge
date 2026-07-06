/*
Purpose:
This file provides the edit-migration experience.

Why:
Users need a way to update migration metadata without leaving the dashboard.

Architecture:
Protected App Shell
↓
Edit Migration Page
↓
Migration Service
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { MigrationForm, type MigrationFormValues } from "@/components/migrations/MigrationForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { migrationService } from "@/services/migrationService";

export function MigrationEditPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const migrationId = Number(id);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const migrationQuery = useQuery({
    queryKey: ["migration", migrationId],
    queryFn: () => migrationService.getById(migrationId),
    enabled: Number.isFinite(migrationId),
  });

  const updateMutation = useMutation({
    mutationFn: (values: MigrationFormValues) =>
      migrationService.update(migrationId, {
        job_name: values.job_name,
        source_database: values.source_database,
        destination_database: values.destination_database,
        status: values.status,
        description: values.description,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["migrations"] });
      await queryClient.invalidateQueries({ queryKey: ["migration", migrationId] });
      navigate(`/migrations/${migrationId}`);
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update migration job.");
    },
  });

  const initialValues = useMemo<MigrationFormValues | undefined>(() => {
    if (!migrationQuery.data) {
      return undefined;
    }

    return {
      job_name: migrationQuery.data.job_name,
      source_database: migrationQuery.data.source_database,
      destination_database: migrationQuery.data.destination_database,
      status: migrationQuery.data.status,
      description: migrationQuery.data.description || "",
    };
  }, [migrationQuery.data]);

  if (migrationQuery.isLoading) {
    return <div className="rounded-lg border border-dashed p-8 text-sm text-muted-foreground">Loading migration details…</div>;
  }

  if (migrationQuery.isError || !initialValues) {
    return (
      <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
        {migrationQuery.error instanceof Error ? migrationQuery.error.message : "Unable to load migration job."}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Edit migration job</h1>
        <p className="mt-2 text-sm text-muted-foreground">Adjust the stored metadata and status for this workflow.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Update migration</CardTitle>
          <CardDescription>Changes are sent to the backend CRUD API and reflected immediately.</CardDescription>
        </CardHeader>
        <CardContent>
          <MigrationForm
            initialValues={initialValues}
            submitLabel="Save changes"
            isSubmitting={updateMutation.isPending}
            errorMessage={errorMessage}
            includeStatus
            onSubmit={(values) => {
              setErrorMessage(null);
              updateMutation.mutate(values);
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
