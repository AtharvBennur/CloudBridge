/*
Purpose:
Provides a premium onboarding dashboard for database endpoints.
Supports Source (stores password in customer SM) and Destination Option A/B configurations.
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cloud, Database, Network, Plus, Server, Sparkles, Trash2, KeyRound } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { databaseConfigService } from "@/services/databaseConfigService";
import { awsConnectionService } from "@/services/awsConnectionService";

export function DatabaseConfigPage() {
  const queryClient = useQueryClient();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formValues, setFormValues] = useState({
    name: "",
    database_type: "POSTGRESQL",
    host: "",
    port: 5432,
    username: "",
    password: "",
    purpose: "SOURCE",
    aws_connection_id: "",
    dest_option: "A", // A = Existing Secret, B = Provision
    secret_name: "",
    secret_arn: "",
    provisioning_config: '{\n  "instance_class": "db.t3.medium",\n  "allocated_storage": 20,\n  "engine_version": "15.4"\n}',
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Queries
  const databaseConfigsQuery = useQuery({
    queryKey: ["database-configs"],
    queryFn: () => databaseConfigService.list(),
  });

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: () => {
      const payload: any = {
        name: formValues.name,
        database_type: formValues.database_type,
        host: formValues.purpose === "DESTINATION" && formValues.dest_option === "B" ? "" : formValues.host,
        port: Number(formValues.port),
        username: formValues.purpose === "DESTINATION" && formValues.dest_option === "B" ? "" : formValues.username,
        purpose: formValues.purpose,
      };

      if (formValues.aws_connection_id) {
        payload.aws_connection_id = Number(formValues.aws_connection_id);
      }

      if (formValues.purpose === "SOURCE") {
        payload.password = formValues.password;
      } else {
        if (formValues.dest_option === "A") {
          if (formValues.secret_arn) payload.secret_arn = formValues.secret_arn;
          if (formValues.secret_name) payload.secret_name = formValues.secret_name;
        } else {
          payload.provisioning_config = formValues.provisioning_config;
        }
      }

      return databaseConfigService.create(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["database-configs"] });
      setSuccessMessage("Database endpoint successfully registered and validated!");
      setErrorMessage(null);
      setIsFormOpen(false);
      // Reset form
      setFormValues((prev) => ({
        ...prev,
        name: "",
        host: "",
        username: "",
        password: "",
        secret_name: "",
        secret_arn: "",
      }));
      setTimeout(() => setSuccessMessage(null), 5000);
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Unable to register database configuration.");
      setSuccessMessage(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => databaseConfigService.remove(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["database-configs"] });
    },
  });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/85 p-6 shadow-soft lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <Server className="h-6 w-6" />
          </div>
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="secondary">AWS Secrets Integration</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">Database Configurations</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Register source or destination endpoints. Source credentials are saved directly into your AWS Secrets Manager; CloudBridge never stores passwords locally.
            </p>
          </div>
        </div>
        <Button onClick={() => setIsFormOpen(!isFormOpen)} variant={isFormOpen ? "outline" : "default"}>
          <Plus className="mr-2 h-4 w-4" />
          {isFormOpen ? "Close panel" : "Onboard database"}
        </Button>
      </div>

      {successMessage && (
        <div className="rounded-2xl border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-600 dark:text-green-400">
          {successMessage}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        {/* Onboarding Panel */}
        {isFormOpen ? (
          <Card className="border-border/70 shadow-soft">
            <CardHeader>
              <CardTitle>Onboard Endpoint</CardTitle>
              <CardDescription>Configure credentials storage and link AWS connection roles.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="db_name">Friendly Endpoint Name</Label>
                <Input
                  id="db_name"
                  value={formValues.name}
                  onChange={(e) => setFormValues({ ...formValues, name: e.target.value })}
                  placeholder="e.g. pgsql-production"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="purpose">Database Purpose</Label>
                  <select
                    id="purpose"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                    value={formValues.purpose}
                    onChange={(e) => setFormValues({ ...formValues, purpose: e.target.value })}
                  >
                    <option value="SOURCE">SOURCE DATABASE</option>
                    <option value="DESTINATION">DESTINATION DATABASE</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="db_type">Database Engine</Label>
                  <select
                    id="db_type"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                    value={formValues.database_type}
                    onChange={(e) => setFormValues({ ...formValues, database_type: e.target.value })}
                  >
                    <option value="POSTGRESQL">PostgreSQL</option>
                    <option value="MYSQL">MySQL</option>
                    <option value="ORACLE">Oracle</option>
                    <option value="SQL_SERVER">SQL Server</option>
                  </select>
                </div>
              </div>

              {/* AWS connection dropdown */}
              <div className="space-y-2">
                <Label htmlFor="aws_connection_id">AWS Connection (for Secrets Manager access)</Label>
                <select
                  id="aws_connection_id"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                  value={formValues.aws_connection_id}
                  onChange={(e) => setFormValues({ ...formValues, aws_connection_id: e.target.value })}
                >
                  <option value="">-- Select AWS Connection --</option>
                  {awsConnectionsQuery.data?.map((conn) => (
                    <option key={conn.id} value={conn.id}>
                      AWS Account: {conn.aws_account_id} ({conn.aws_region})
                    </option>
                  ))}
                </select>
                {formValues.purpose === "SOURCE" && !formValues.aws_connection_id && (
                  <p className="text-xs text-amber-500">AWS Connection is required to push source passwords to Secrets Manager.</p>
                )}
              </div>

              {/* Conditional Inputs based on Purpose */}
              {formValues.purpose === "SOURCE" ? (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="col-span-2 space-y-2">
                      <Label htmlFor="host">Host / Endpoint</Label>
                      <Input
                        id="host"
                        value={formValues.host}
                        onChange={(e) => setFormValues({ ...formValues, host: e.target.value })}
                        placeholder="db.example.com"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="port">Port</Label>
                      <Input
                        id="port"
                        type="number"
                        value={formValues.port}
                        onChange={(e) => setFormValues({ ...formValues, port: Number(e.target.value) })}
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="username">Database Username</Label>
                      <Input
                        id="username"
                        value={formValues.username}
                        onChange={(e) => setFormValues({ ...formValues, username: e.target.value })}
                        placeholder="postgres"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="password">Password</Label>
                      <Input
                        id="password"
                        type="password"
                        value={formValues.password}
                        onChange={(e) => setFormValues({ ...formValues, password: e.target.value })}
                        placeholder="••••••••"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                /* Destination fields */
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Destination Options</Label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 text-sm font-medium">
                        <input
                          type="radio"
                          name="dest_option"
                          value="A"
                          checked={formValues.dest_option === "A"}
                          onChange={() => setFormValues({ ...formValues, dest_option: "A" })}
                        />
                        Option A: Existing secret in AWS Secrets Manager
                      </label>
                      <label className="flex items-center gap-2 text-sm font-medium">
                        <input
                          type="radio"
                          name="dest_option"
                          value="B"
                          checked={formValues.dest_option === "B"}
                          onChange={() => setFormValues({ ...formValues, dest_option: "B" })}
                        />
                        Option B: CloudBridge provisions target DB
                      </label>
                    </div>
                  </div>

                  {formValues.dest_option === "A" ? (
                    <div className="space-y-4">
                      <div className="grid gap-4 md:grid-cols-3">
                        <div className="col-span-2 space-y-2">
                          <Label htmlFor="host">Host</Label>
                          <Input
                            id="host"
                            value={formValues.host}
                            onChange={(e) => setFormValues({ ...formValues, host: e.target.value })}
                            placeholder="staging-db.example.com"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="port">Port</Label>
                          <Input
                            id="port"
                            type="number"
                            value={formValues.port}
                            onChange={(e) => setFormValues({ ...formValues, port: Number(e.target.value) })}
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="username">Database Username</Label>
                        <Input
                          id="username"
                          value={formValues.username}
                          onChange={(e) => setFormValues({ ...formValues, username: e.target.value })}
                          placeholder="postgres"
                        />
                      </div>

                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="secret_arn">Secret ARN (Optional)</Label>
                          <Input
                            id="secret_arn"
                            value={formValues.secret_arn}
                            onChange={(e) => setFormValues({ ...formValues, secret_arn: e.target.value })}
                            placeholder="arn:aws:secretsmanager:..."
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="secret_name">Secret Name (or Secret ARN)</Label>
                          <Input
                            id="secret_name"
                            value={formValues.secret_name}
                            onChange={(e) => setFormValues({ ...formValues, secret_name: e.target.value })}
                            placeholder="cloudbridge/db-secret"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Label htmlFor="provisioning_config">RDS Provisioning Specification (JSON)</Label>
                      <textarea
                        id="provisioning_config"
                        rows={5}
                        className="w-full rounded-md border border-input bg-background p-2 font-mono text-xs shadow-sm"
                        value={formValues.provisioning_config}
                        onChange={(e) => setFormValues({ ...formValues, provisioning_config: e.target.value })}
                      />
                    </div>
                  )}
                </div>
              )}

              {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

              <Button
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending}
                className="w-full"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                {createMutation.isPending ? "Validating & storing secret..." : "Validate & Register Endpoint"}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-border/70 shadow-soft">
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="rounded-full bg-primary/10 p-4 text-primary">
                <Database className="h-8 w-8" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">Endpoint Registration</h3>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Onboard source databases or connect existing secrets for your target environments to begin migrations.
              </p>
              <Button onClick={() => setIsFormOpen(true)} className="mt-6">
                <Plus className="mr-2 h-4 w-4" />
                Register Endpoint
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Existing endpoints overview */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <CardTitle>Registered endpoints</CardTitle>
            <CardDescription>Onboarded databases and Secret ARNs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {databaseConfigsQuery.isLoading && (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}

            {!databaseConfigsQuery.isLoading && databaseConfigsQuery.data?.length === 0 && (
              <div className="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                No database endpoints registered yet. Start with the onboarding form.
              </div>
            )}

            {databaseConfigsQuery.data?.map((config) => (
              <div key={config.id} className="rounded-2xl border border-border/70 bg-background/80 p-4 shadow-sm hover:border-primary/45 transition">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h4 className="font-semibold text-foreground">{config.name}</h4>
                    <p className="text-xs text-muted-foreground">{config.database_type} • Host: {config.host}:{config.port}</p>
                  </div>
                  <Badge variant={config.purpose === "SOURCE" ? "success" : "indigo"}>
                    {config.purpose}
                  </Badge>
                </div>

                <div className="mt-3 space-y-2 border-t pt-3 text-xs text-muted-foreground">
                  {config.secret_arn && (
                    <div className="flex items-center gap-1.5">
                      <KeyRound className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span className="font-medium text-foreground">AWS Secret ARN:</span>
                      <span className="truncate max-w-[240px]" title={config.secret_arn}>{config.secret_arn}</span>
                    </div>
                  )}
                  {config.provisioning_config && (
                    <div className="rounded border bg-muted/40 p-2 font-mono text-[10px] text-foreground">
                      <span className="font-bold">Provisioning Spec:</span> {config.provisioning_config}
                    </div>
                  )}
                  {config.aws_connection_id && (
                    <div>
                      <span className="font-medium text-foreground">Linked AWS Conn ID:</span> {config.aws_connection_id}
                    </div>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-end">
                  <Button
                    onClick={() => deleteMutation.mutate(config.id)}
                    disabled={deleteMutation.isPending}
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    Delete Config
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
