/*
Purpose:
This file provides a polished AWS account connection experience.

Why:
Customers need a guided page that looks and feels like a modern cloud console for onboarding metadata.

Architecture:
Protected App Shell
↓
AWS Connection Page
↓
AWS Connection Service
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cloud, Network, PencilLine, Plus, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { awsConnectionService } from "@/services/awsConnectionService";

function statusVariant(status: string) {
  switch (status) {
    case "CONNECTED":
      return "success";
    case "PENDING":
      return "warning";
    case "FAILED":
      return "destructive";
    default:
      return "secondary";
  }
}

export function AWSConnectionPage() {
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState({
    aws_account_id: "",
    aws_region: "",
    role_arn: "",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => awsConnectionService.create(formValues),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
      setFormValues({ aws_account_id: "", aws_region: "", role_arn: "" });
      setErrorMessage(null);
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create AWS connection.");
    },
  });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/80 p-6 shadow-sm lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <Network className="h-5 w-5" />
          </div>
          <div>
            <div className="mb-3 flex items-center gap-2">
              <Badge variant="secondary">Sprint 4</Badge>
              <Badge variant="warning">Metadata only</Badge>
            </div>
            <h1 className="text-3xl font-semibold">AWS connections</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Register AWS account metadata for future enterprise onboarding and deployment workflows. No AWS API calls are made yet.
            </p>
          </div>
        </div>
        <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
          <Plus className="mr-2 h-4 w-4" />
          {createMutation.isPending ? "Saving…" : "New connection"}
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                <Cloud className="h-5 w-5" />
              </div>
              <div>
                <CardTitle>Connect AWS account</CardTitle>
                <CardDescription>Store the onboarding details for the target account.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="aws_account_id">AWS Account ID</Label>
                <Input
                  id="aws_account_id"
                  value={formValues.aws_account_id}
                  onChange={(event) => setFormValues((current) => ({ ...current, aws_account_id: event.target.value }))}
                  placeholder="123456789012"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="aws_region">Region</Label>
                <Input
                  id="aws_region"
                  value={formValues.aws_region}
                  onChange={(event) => setFormValues((current) => ({ ...current, aws_region: event.target.value }))}
                  placeholder="us-east-1"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="role_arn">Role ARN</Label>
              <Input
                id="role_arn"
                value={formValues.role_arn}
                onChange={(event) => setFormValues((current) => ({ ...current, role_arn: event.target.value }))}
                placeholder="arn:aws:iam::123456789012:role/CloudBridgeRole"
              />
            </div>

            {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}

            <div className="rounded-2xl border border-border/70 bg-muted/40 p-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-2 font-medium text-foreground">
                <ShieldCheck className="h-4 w-4 text-primary" />
                Connection policy preview
              </div>
              <p className="mt-2">The system will generate a UUID-based external ID and store it locally for future Cross-Account IAM integration.</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Account overview</CardTitle>
                <CardDescription>Current connection state and onboarding metadata.</CardDescription>
              </div>
              <Button variant="ghost" size="icon" aria-label="Refresh connections">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {awsConnectionsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : null}

            {awsConnectionsQuery.isError ? (
              <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                {awsConnectionsQuery.error instanceof Error ? awsConnectionsQuery.error.message : "Unable to load AWS connections."}
              </div>
            ) : null}

            {!awsConnectionsQuery.isLoading && !awsConnectionsQuery.isError && awsConnectionsQuery.data?.length === 0 ? (
              <div className="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                No AWS connections yet. Start with the form to onboard your first account.
              </div>
            ) : null}

            {!awsConnectionsQuery.isLoading && !awsConnectionsQuery.isError && awsConnectionsQuery.data?.length ? (
              <div className="space-y-3">
                {awsConnectionsQuery.data.map((connection) => (
                  <div key={connection.id} className="rounded-2xl border border-border/70 bg-background/80 p-4 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{connection.aws_account_id}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{connection.aws_region}</p>
                      </div>
                      <Badge variant={statusVariant(connection.connection_status)}>{connection.connection_status}</Badge>
                    </div>
                    <div className="mt-4 grid gap-3 text-sm text-muted-foreground md:grid-cols-2">
                      <div>
                        <p className="font-medium text-foreground">Role ARN</p>
                        <p className="mt-1 break-all">{connection.role_arn}</p>
                      </div>
                      <div>
                        <p className="font-medium text-foreground">External ID</p>
                        <p className="mt-1 break-all">{connection.external_id}</p>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button variant="outline" size="sm">
                        <PencilLine className="mr-2 h-4 w-4" />
                        Edit Connection
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete Connection
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
