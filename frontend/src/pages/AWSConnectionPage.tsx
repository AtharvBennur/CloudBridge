/*
Purpose:
AWS Connection Dashboard.
Implements AssumeRole testing, dynamic IAM policies simulator, region verification,
and direct browser downloads for generated CloudFormation templates.
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cloud, Network, PencilLine, Plus, RefreshCw, ShieldCheck, Trash2, Download, AlertCircle, Play, Info } from "lucide-react";
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
    case "DISCONNECTED":
      return "secondary";
    default:
      return "secondary";
  }
}

export function AWSConnectionPage() {
  const queryClient = useQueryClient();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formValues, setFormValues] = useState({
    aws_account_id: "",
    aws_region: "us-east-1",
    role_arn: "",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeResults, setActiveResults] = useState<Record<number, any>>({});
  const [loadingAction, setLoadingAction] = useState<Record<string, boolean>>({});

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => awsConnectionService.create(formValues),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
      setFormValues({ aws_account_id: "", aws_region: "us-east-1", role_arn: "" });
      setErrorMessage(null);
      setIsFormOpen(false);
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create AWS connection.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => awsConnectionService.remove(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    },
  });

  // Action Triggers
  const handleTestConnection = async (id: number) => {
    const key = `test-${id}`;
    setLoadingAction((prev) => ({ ...prev, [key]: true }));
    try {
      const res = await awsConnectionService.connect(id);
      setActiveResults((prev) => ({ ...prev, [id]: { type: "test", data: res } }));
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    } catch (err: any) {
      setActiveResults((prev) => ({ ...prev, [id]: { type: "error", message: err.message } }));
    } finally {
      setLoadingAction((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleValidatePermissions = async (id: number) => {
    const key = `validate-${id}`;
    setLoadingAction((prev) => ({ ...prev, [key]: true }));
    try {
      const res = await awsConnectionService.validate(id);
      setActiveResults((prev) => ({ ...prev, [id]: { type: "validate", data: res } }));
    } catch (err: any) {
      setActiveResults((prev) => ({ ...prev, [id]: { type: "error", message: err.message } }));
    } finally {
      setLoadingAction((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleDisconnect = async (id: number) => {
    const key = `disconnect-${id}`;
    setLoadingAction((prev) => ({ ...prev, [key]: true }));
    try {
      await awsConnectionService.disconnect(id);
      setActiveResults((prev) => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    } catch (err: any) {
      alert("Failed to disconnect: " + err.message);
    } finally {
      setLoadingAction((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleDownloadCF = async (id: number) => {
    try {
      const data = await awsConnectionService.getCloudformationTemplate(id);
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
        JSON.stringify(data.template, null, 2)
      )}`;
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", jsonString);
      downloadAnchor.setAttribute("download", data.download_filename);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert("Failed to fetch template: " + err.message);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Top Banner Card */}
      <div className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/85 p-6 shadow-soft lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <Network className="h-6 w-6" />
          </div>
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="success">Active Plane</Badge>
              <Badge variant="secondary">AssumeRole Active</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">AWS IAM Onboarding</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Configure cross-account delegation roles. CloudBridge assumes this IAM role using your unique generated External ID to configure database secrets.
            </p>
          </div>
        </div>
        <Button onClick={() => setIsFormOpen(!isFormOpen)} variant={isFormOpen ? "outline" : "default"}>
          <Plus className="mr-2 h-4 w-4" />
          {isFormOpen ? "Close panel" : "Onboard AWS Account"}
        </Button>
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        {/* Form Panel */}
        {isFormOpen ? (
          <Card className="border-border/70 shadow-soft">
            <CardHeader>
              <CardTitle>Connect AWS Account</CardTitle>
              <CardDescription>Specify the target Account ID and delegating role.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="aws_account_id">AWS Account ID</Label>
                  <Input
                    id="aws_account_id"
                    value={formValues.aws_account_id}
                    onChange={(event) => setFormValues((curr) => ({ ...curr, aws_account_id: event.target.value }))}
                    placeholder="123456789012"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="aws_region">Region</Label>
                  <Input
                    id="aws_region"
                    value={formValues.aws_region}
                    onChange={(event) => setFormValues((curr) => ({ ...curr, aws_region: event.target.value }))}
                    placeholder="us-east-1"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="role_arn">Delegation Role ARN</Label>
                <Input
                  id="role_arn"
                  value={formValues.role_arn}
                  onChange={(event) => setFormValues((curr) => ({ ...curr, role_arn: event.target.value }))}
                  placeholder="arn:aws:iam::123456789012:role/CloudBridgeMigrationRole"
                />
              </div>

              {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}

              <div className="rounded-xl border border-border/70 bg-muted/40 p-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-2 font-medium text-foreground mb-1">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  Security Guarantee
                </div>
                The credentials connection setup generates a unique UUID-based External ID requirement to protect against the confused deputy problem.
              </div>

              <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending} className="w-full">
                {createMutation.isPending ? "Registering account..." : "Onboard AWS Connection"}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-border/70 shadow-soft">
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="rounded-full bg-primary/10 p-4 text-primary">
                <Cloud className="h-8 w-8" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">AWS Onboarding</h3>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Connect your AWS accounts securely. Register your target configuration parameters to start generating IAM automation policies.
              </p>
              <Button onClick={() => setIsFormOpen(true)} className="mt-6">
                <Plus className="mr-2 h-4 w-4" />
                Add AWS Connection
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Overview List Panel */}
        <Card className="border-border/70 shadow-soft">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Account Overview</CardTitle>
                <CardDescription>Onboarded IAM accounts and active validations.</CardDescription>
              </div>
              <Button variant="ghost" size="icon" onClick={() => queryClient.invalidateQueries({ queryKey: ["aws-connections"] })} aria-label="Refresh connections">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {awsConnectionsQuery.isLoading && (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}

            {!awsConnectionsQuery.isLoading && awsConnectionsQuery.data?.length === 0 && (
              <div className="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                No AWS accounts connected yet. Add a connection setup using the form.
              </div>
            )}

            {awsConnectionsQuery.data?.map((connection) => {
              const res = activeResults[connection.id];
              return (
                <div key={connection.id} className="rounded-2xl border border-border/70 bg-background/80 p-4 shadow-sm hover:border-primary/45 transition">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-foreground">Account ID: {connection.aws_account_id}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">Region: {connection.aws_region}</p>
                    </div>
                    <Badge variant={statusVariant(connection.connection_status)}>{connection.connection_status}</Badge>
                  </div>

                  <div className="mt-4 grid gap-3 text-xs text-muted-foreground md:grid-cols-2 border-t pt-3">
                    <div>
                      <p className="font-medium text-foreground">Role ARN</p>
                      <p className="mt-1 break-all bg-muted/40 p-1.5 rounded">{connection.role_arn}</p>
                    </div>
                    <div>
                      <p className="font-medium text-foreground">External ID</p>
                      <p className="mt-1 break-all bg-muted/40 p-1.5 rounded font-mono">{connection.external_id}</p>
                    </div>
                  </div>

                  {/* Dynamic Action Response Feed */}
                  {res && (
                    <div className="mt-3 rounded-xl border p-3 text-xs">
                      {res.type === "test" && (
                        <div className="space-y-1.5">
                          <p className="font-semibold text-green-600 dark:text-green-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            AssumeRole Test Passed
                          </p>
                          <p className="text-[10px] text-muted-foreground">
                            Session Assumed: {res.data.details?.credentials?.AccessKeyId ? "true" : "false"}
                          </p>
                        </div>
                      )}
                      {res.type === "validate" && (
                        <div className="space-y-1.5">
                          <p className="font-semibold text-primary flex items-center gap-1">
                            <Info className="h-3.5 w-3.5" />
                            IAM Permissions Report ({res.data.status})
                          </p>
                          <div className="grid grid-cols-2 gap-1 font-mono text-[10px] mt-1">
                            {Object.entries(res.data.permissions || {}).map(([perm, ok]) => (
                              <div key={perm} className="flex items-center gap-1">
                                <span className={ok ? "text-green-500" : "text-red-500"}>{ok ? "✓" : "✗"}</span>
                                <span>{perm}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {res.type === "error" && (
                        <p className="text-destructive font-medium flex items-center gap-1">
                          <AlertCircle className="h-3.5 w-3.5" />
                          Error: {res.message}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Actions Bar */}
                  <div className="mt-4 flex flex-wrap gap-2 border-t pt-3 justify-between">
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleTestConnection(connection.id)}
                        disabled={loadingAction[`test-${connection.id}`]}
                        variant="outline"
                        size="sm"
                      >
                        <Play className="mr-1.5 h-3.5 w-3.5 text-green-500" />
                        {loadingAction[`test-${connection.id}`] ? "Testing..." : "Test STS"}
                      </Button>

                      <Button
                        onClick={() => handleValidatePermissions(connection.id)}
                        disabled={loadingAction[`validate-${connection.id}`]}
                        variant="outline"
                        size="sm"
                      >
                        <ShieldCheck className="mr-1.5 h-3.5 w-3.5 text-primary" />
                        {loadingAction[`validate-${connection.id}`] ? "Validating..." : "Validate IAM"}
                      </Button>

                      <Button
                        onClick={() => handleDownloadCF(connection.id)}
                        variant="outline"
                        size="sm"
                      >
                        <Download className="mr-1.5 h-3.5 w-3.5" />
                        Download CloudFormation
                      </Button>
                    </div>

                    <div className="flex gap-2">
                      {connection.connection_status === "CONNECTED" ? (
                        <Button
                          onClick={() => handleDisconnect(connection.id)}
                          variant="ghost"
                          size="sm"
                          className="text-amber-500 hover:bg-amber-500/10"
                        >
                          Disconnect
                        </Button>
                      ) : (
                        <Button
                          onClick={() => deleteMutation.mutate(connection.id)}
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CheckCircle2(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}
