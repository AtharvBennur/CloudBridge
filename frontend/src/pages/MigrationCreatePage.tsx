/*
Purpose:
This file provides the create-migration experience.

Why:
Users need a guided form to register new migration jobs with the backend.

Architecture:
Protected App Shell
↓
Create Migration Page
↓
Migration Service
*/

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { MigrationForm, type MigrationFormValues } from "@/components/migrations/MigrationForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { migrationService } from "@/services/migrationService";

export function MigrationCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (values: MigrationFormValues) =>
      migrationService.create({
        job_name: values.job_name,
        source_database: values.source_database,
        destination_database: values.destination_database,
        description: values.description || undefined,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["migrations"] });
      navigate("/migrations");
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create migration job.");
    },
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Create migration job</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Register migration metadata so the platform can track each transformation workstream.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Migration details</CardTitle>
          <CardDescription>Fields mirror the backend schema and validation rules.</CardDescription>
        </CardHeader>
        <CardContent>
          <MigrationForm
            initialValues={{
              job_name: "",
              source_database: "",
              destination_database: "",
              description: "",
            }}
            submitLabel="Create migration"
            isSubmitting={createMutation.isPending}
            errorMessage={errorMessage}
            onSubmit={(values) => {
              setErrorMessage(null);
              createMutation.mutate(values);
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
