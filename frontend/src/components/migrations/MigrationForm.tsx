/*
Purpose:
This file provides a shared form for creating and editing migration jobs.

Why:
The create and edit flows share the same fields, so one reusable form keeps the UX consistent.

Architecture:
Migration Create/Edit Pages
↓
Shared Migration Form
*/

import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface MigrationFormValues {
  job_name: string;
  source_database: string;
  destination_database: string;
  status?: string;
  description: string;
}

interface MigrationFormProps {
  initialValues: MigrationFormValues;
  submitLabel: string;
  isSubmitting: boolean;
  errorMessage?: string | null;
  includeStatus?: boolean;
  onSubmit: (values: MigrationFormValues) => void;
}

const emptyValues = (initialValues: MigrationFormValues): MigrationFormValues => ({
  job_name: initialValues.job_name || "",
  source_database: initialValues.source_database || "",
  destination_database: initialValues.destination_database || "",
  status: initialValues.status || "PENDING",
  description: initialValues.description || "",
});

export function MigrationForm({
  initialValues,
  submitLabel,
  isSubmitting,
  errorMessage,
  includeStatus = false,
  onSubmit,
}: MigrationFormProps) {
  const [values, setValues] = useState<MigrationFormValues>(() => emptyValues(initialValues));

  useEffect(() => {
    setValues(emptyValues(initialValues));
  }, [initialValues]);

  const handleChange = (field: keyof MigrationFormValues, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(values);
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="job_name">Job name</Label>
          <Input
            id="job_name"
            value={values.job_name}
            onChange={(event) => handleChange("job_name", event.target.value)}
            placeholder="Example: Customer Data Sync"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="source_database">Source database</Label>
          <Input
            id="source_database"
            value={values.source_database}
            onChange={(event) => handleChange("source_database", event.target.value)}
            placeholder="Example: postgres-prod"
            required
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="destination_database">Destination database</Label>
          <Input
            id="destination_database"
            value={values.destination_database}
            onChange={(event) => handleChange("destination_database", event.target.value)}
            placeholder="Example: postgres-staging"
            required
          />
        </div>

        {includeStatus ? (
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <select
              id="status"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
              value={values.status || "PENDING"}
              onChange={(event) => handleChange("status", event.target.value)}
            >
              <option value="PENDING">PENDING</option>
              <option value="RUNNING">RUNNING</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="FAILED">FAILED</option>
            </select>
          </div>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <textarea
          id="description"
          className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
          value={values.description}
          onChange={(event) => handleChange("description", event.target.value)}
          placeholder="Optional notes about this migration job"
        />
      </div>

      {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}

      <div className="flex items-center justify-end gap-3 pt-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
