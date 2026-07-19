/*
Purpose:
Enterprise-grade database endpoint registration with deep validation,
table preview, and sensitive data masking.
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Database,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Plus,
  Server,
  Shield,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { databaseConfigService } from "@/services/databaseConfigService";
import type {
  DestinationValidationResult,
  SourceValidationResult,
  ValidationCheck,
} from "@/services/databaseConfigService";
import { awsConnectionService } from "@/services/awsConnectionService";

/** Strip protocol and trailing slash from a host value */
function sanitizeHost(raw: string): string {
  return raw.replace(/^https?:\/\//, "").replace(/\/+$/, "");
}

/** Default ports per database engine */
const DEFAULT_PORTS: Record<string, number> = {
  POSTGRESQL: 5432,
  MYSQL: 3306,
  ORACLE: 1521,
  SQL_SERVER: 1433,
};

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
    database_name: "",
    purpose: "SOURCE",
    aws_connection_id: "",
    dest_option: "A",
    secret_name: "",
    secret_arn: "",
    provisioning_config: '{\n  "instance_class": "db.t3.medium",\n  "allocated_storage": 20,\n  "engine_version": "15.4"\n}',
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // Validation state
  const [sourceValidation, setSourceValidation] = useState<SourceValidationResult | null>(null);
  const [destValidation, setDestValidation] = useState<DestinationValidationResult | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const databaseConfigsQuery = useQuery({
    queryKey: ["database-configs"],
    queryFn: () => databaseConfigService.list(),
  });

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  // ── Validation mutation ──────────────────────────────────────────────────
  const validateMutation = useMutation({
    mutationFn: async () => {
      setSourceValidation(null);
      setDestValidation(null);
      setValidationError(null);

      const payload = {
        database_type: formValues.database_type,
        host: sanitizeHost(formValues.host),
        port: Number(formValues.port),
        username: formValues.username,
        password: formValues.password,
        database_name: formValues.database_name || undefined,
      };

      if (formValues.purpose === "SOURCE") {
        return databaseConfigService.validateSource(payload);
      } else {
        return databaseConfigService.validateDestination(payload);
      }
    },
    onSuccess: (data) => {
      if ("selectedTable" in data) {
        setSourceValidation(data as SourceValidationResult);
      } else {
        setDestValidation(data as DestinationValidationResult);
      }
    },
    onError: (error: unknown) => {
      setValidationError(error instanceof Error ? error.message : "Validation failed.");
    },
  });

  // ── Create mutation (only after successful validation) ───────────────────
  const createMutation = useMutation({
    mutationFn: () => {
      const payload: any = {
        name: formValues.name,
        database_type: formValues.database_type,
        host: formValues.host,
        port: Number(formValues.port),
        username: formValues.username,
        password: formValues.password,
        purpose: formValues.purpose,
      };

      if (formValues.aws_connection_id) {
        payload.aws_connection_id = Number(formValues.aws_connection_id);
      }
      if (formValues.database_name) {
        payload.database_name = formValues.database_name;
      }

      if (formValues.purpose === "DESTINATION") {
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
      setSourceValidation(null);
      setDestValidation(null);
      setFormValues((prev) => ({
        ...prev,
        name: "",
        host: "",
        username: "",
        password: "",
        database_name: "",
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

  const isSourceValidated = sourceValidation?.connection === "success";
  const isDestValidated = destValidation?.connection === "success" && destValidation.databaseExists;
  const canRegister = formValues.purpose === "SOURCE" ? isSourceValidated : isDestValidated;

  const handlePurposeChange = (purpose: string) => {
    setFormValues({ ...formValues, purpose });
    setSourceValidation(null);
    setDestValidation(null);
    setValidationError(null);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/85 p-6 shadow-soft lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <Server className="h-6 w-6" />
          </div>
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="secondary">Deep Validation</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">Database Configurations</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Register source or destination endpoints with full connectivity validation. Source databases show table previews with automatic sensitive data masking.
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
          <div className="space-y-6">
            <Card className="border-border/70 shadow-soft">
              <CardHeader>
                <CardTitle>Onboard Endpoint</CardTitle>
                <CardDescription>Configure and validate your database connection.</CardDescription>
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
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm"
                      value={formValues.purpose}
                      onChange={(e) => handlePurposeChange(e.target.value)}
                    >
                      <option value="SOURCE">SOURCE DATABASE</option>
                      <option value="DESTINATION">DESTINATION DATABASE</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="db_type">Database Engine</Label>
                    <select
                      id="db_type"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm"
                      value={formValues.database_type}
                      onChange={(e) => {
                        const newType = e.target.value;
                        setFormValues({
                          ...formValues,
                          database_type: newType,
                          port: DEFAULT_PORTS[newType] ?? formValues.port,
                        });
                        setSourceValidation(null);
                        setDestValidation(null);
                      }}
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
                  <Label htmlFor="aws_connection_id">AWS Connection (for Secrets Manager)</Label>
                  <select
                    id="aws_connection_id"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm"
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
                </div>

                {/* Connection fields */}
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="col-span-2 space-y-2">
                    <Label htmlFor="host">Host / Endpoint</Label>
                    <Input
                      id="host"
                      value={formValues.host}
                      onChange={(e) => setFormValues({ ...formValues, host: sanitizeHost(e.target.value) })}
                      placeholder="mydb.cm1406ikomix.us-east-1.rds.amazonaws.com"
                    />
                    <p className="text-xs text-muted-foreground">
                      Use the RDS DNS endpoint, not an IP address. Find it in the AWS Console under RDS → Connectivity.
                    </p>
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
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        value={formValues.password}
                        onChange={(e) => setFormValues({ ...formValues, password: e.target.value })}
                        placeholder="Enter password"
                        className="pr-10"
                      />
                      <button
                        type="button"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                {formValues.purpose === "SOURCE" && (
                  <div className="space-y-2">
                    <Label htmlFor="database_name">Database Name</Label>
                    <Input
                      id="database_name"
                      value={formValues.database_name}
                      onChange={(e) => setFormValues({ ...formValues, database_name: e.target.value })}
                      placeholder="e.g. production_db"
                    />
                    <p className="text-xs text-muted-foreground">The actual database name on the server (required for migration).</p>
                  </div>
                )}

                {validationError && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                    {validationError}
                  </div>
                )}

                {/* Validate button */}
                <Button
                  onClick={() => validateMutation.mutate()}
                  disabled={validateMutation.isPending || !formValues.host || !formValues.username || !formValues.password}
                  className="w-full"
                  variant="outline"
                >
                  {validateMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Validating connection...
                    </>
                  ) : (
                    <>
                      <Shield className="mr-2 h-4 w-4" />
                      Validate Connection
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* ── Validation Results ──────────────────────────────────────── */}
            {validateMutation.isPending && (
              <ValidationProgress checks={[]} />
            )}

            {sourceValidation && (
              <SourceValidationCard result={sourceValidation} />
            )}

            {destValidation && (
              <DestinationValidationCard result={destValidation} />
            )}

            {/* ── Register button (only after validation) ─────────────────── */}
            {canRegister && (
              <Card className="border-green-500/30 shadow-soft">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="h-6 w-6 text-green-500" />
                      <div>
                        <p className="font-semibold text-green-600 dark:text-green-400">
                          Validation passed
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Ready to register this endpoint.
                        </p>
                      </div>
                    </div>
                    <Button
                      onClick={() => createMutation.mutate()}
                      disabled={createMutation.isPending}
                    >
                      <Sparkles className="mr-2 h-4 w-4" />
                      {createMutation.isPending ? "Registering..." : "Register Endpoint"}
                    </Button>
                  </div>
                  {errorMessage && (
                    <p className="mt-2 text-sm text-destructive">{errorMessage}</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          <Card className="border-border/70 shadow-soft">
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="rounded-full bg-primary/10 p-4 text-primary">
                <Database className="h-8 w-8" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">Endpoint Registration</h3>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Onboard source or destination databases with deep validation, table previews, and permission checks.
              </p>
              <Button onClick={() => setIsFormOpen(true)} className="mt-6">
                <Plus className="mr-2 h-4 w-4" />
                Register Endpoint
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Registered endpoints list */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <CardTitle>Registered endpoints</CardTitle>
            <CardDescription>Onboarded databases and their configurations.</CardDescription>
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
                No database endpoints registered yet.
              </div>
            )}

            {databaseConfigsQuery.data?.map((config) => (
              <div key={config.id} className="rounded-2xl border border-border/70 bg-background/80 p-4 shadow-sm transition hover:border-primary/45">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h4 className="font-semibold text-foreground">{config.name}</h4>
                    <p className="text-xs text-muted-foreground">
                      {config.database_type} - {config.host}:{config.port}
                      {config.database_name && ` - DB: ${config.database_name}`}
                    </p>
                  </div>
                  <Badge variant={config.purpose === "SOURCE" ? "success" : "indigo"}>
                    {config.purpose}
                  </Badge>
                </div>

                <div className="mt-3 space-y-2 border-t pt-3 text-xs text-muted-foreground">
                  {config.secret_arn && (
                    <div className="flex items-center gap-1.5">
                      <KeyRound className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span className="font-medium text-foreground">Secret ARN:</span>
                      <span className="truncate max-w-[240px]" title={config.secret_arn}>{config.secret_arn}</span>
                    </div>
                  )}
                  {config.aws_connection_id && (
                    <div>
                      <span className="font-medium text-foreground">AWS Conn ID:</span> {config.aws_connection_id}
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
                    Delete
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

// ── Validation Progress (loading animation) ─────────────────────────────────

function ValidationProgress({ checks }: { checks: ValidationCheck[] }) {
  const steps = [
    "Connecting to host...",
    "Authenticating credentials...",
    "Checking permissions...",
    "Reading metadata...",
    "Fetching sample data...",
  ];

  return (
    <Card className="border-border/70 shadow-soft">
      <CardContent className="pt-6">
        <div className="flex items-center gap-3 mb-4">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <p className="font-medium">Validating database connection...</p>
        </div>
        <div className="space-y-3">
          {steps.map((step, i) => {
            const check = checks[i];
            const isDone = check !== undefined;
            const isPassed = check?.passed;

            return (
              <div key={i} className="flex items-center gap-3">
                {isDone ? (
                  isPassed ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                  )
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground/50 shrink-0 animate-pulse" />
                )}
                <span className={`text-sm ${isDone ? "text-foreground" : "text-muted-foreground"}`}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Source Validation Card ──────────────────────────────────────────────────

function SourceValidationCard({ result }: { result: SourceValidationResult }) {
  if (result.connection !== "success") {
    return (
      <Card className="border-destructive/30 shadow-soft">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <p className="font-medium text-destructive">Connection Failed</p>
          </div>
          <div className="space-y-2">
            {result.checks.map((check, i) => (
              <div key={i} className="flex items-center gap-3">
                {check.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                )}
                <span className="text-sm">{check.label}</span>
                {check.detail && <span className="text-xs text-muted-foreground">({check.detail})</span>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-green-500/30 shadow-soft">
      <CardContent className="pt-6">
        {/* Success header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="rounded-full bg-green-500/10 p-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
          </div>
          <div>
            <p className="font-semibold text-green-600 dark:text-green-400">Connection Successful</p>
            <p className="text-sm text-muted-foreground">Source Database: {result.database}</p>
          </div>
        </div>

        {/* Validation checks */}
        <div className="mb-4 space-y-2 rounded-lg border border-border/50 bg-muted/30 p-3">
          {result.checks.map((check, i) => (
            <div key={i} className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
              <span className="text-sm">{check.label}</span>
            </div>
          ))}
        </div>

        {/* Table preview */}
        {result.selectedTable && result.columns.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold">{result.selectedTable}</h4>
                <p className="text-xs text-muted-foreground">
                  {result.rowCount !== null ? `${result.rowCount} rows` : "Sample data"} - {result.columns.length} columns
                  {result.tables.length > 1 && ` - ${result.tables.length} tables discovered`}
                </p>
              </div>
            </div>

            {/* Data table */}
            <div className="overflow-x-auto rounded-lg border border-border/50">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    {result.columns.map((col) => (
                      <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground">
                        {col}
                        {result.maskedColumns.includes(col) && (
                          <span className="ml-1 text-xs text-amber-500" title="Masked">*</span>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.sampleRows.map((row, i) => (
                    <tr key={i} className="border-t border-border/30">
                      {result.columns.map((col) => (
                        <td key={col} className="px-3 py-2 text-foreground/80">
                          {result.maskedColumns.includes(col) ? (
                            <span className="text-amber-600 dark:text-amber-400">{String(row[col])}</span>
                          ) : (
                            String(row[col] ?? "NULL")
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Masking warning */}
            {result.maskedColumns.length > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                Sensitive columns ({result.maskedColumns.join(", ")}) are automatically masked for security.
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Destination Validation Card ─────────────────────────────────────────────

function DestinationValidationCard({ result }: { result: DestinationValidationResult }) {
  if (result.connection !== "success") {
    return (
      <Card className="border-destructive/30 shadow-soft">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <p className="font-medium text-destructive">Connection Failed</p>
          </div>
          <div className="space-y-2">
            {result.checks.map((check, i) => (
              <div key={i} className="flex items-center gap-3">
                {check.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                )}
                <span className="text-sm">{check.label}</span>
                {check.detail && <span className="text-xs text-muted-foreground">({check.detail})</span>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-green-500/30 shadow-soft">
      <CardContent className="pt-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="rounded-full bg-green-500/10 p-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
          </div>
          <div>
            <p className="font-semibold text-green-600 dark:text-green-400">Destination Ready</p>
            <p className="text-sm text-muted-foreground">
              {result.databaseExists ? "Database exists and is accessible." : "Database check completed."}
            </p>
          </div>
        </div>

        <div className="space-y-2 rounded-lg border border-border/50 bg-muted/30 p-3">
          {result.checks.map((check, i) => (
            <div key={i} className="flex items-center gap-2">
              {check.passed ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5 text-destructive shrink-0" />
              )}
              <span className="text-sm">{check.label}</span>
            </div>
          ))}
        </div>

        {result.writePermission && result.readPermission && (
          <p className="mt-3 text-sm text-muted-foreground">
            Ready to receive migrated data.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
