/*
Purpose:
AWS Connection Onboarding Wizard.

Implements a complete production-grade workflow:
1. Enter AWS Account ID + Region
2. Download CloudFormation template
3. Customer deploys stack in their AWS account
4. Paste generated Role ARN from stack output
5. Test STS AssumeRole — only show Connected after real success
*/

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Cloud,
  Network,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Download,
  AlertCircle,
  Play,
  Info,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Copy,
  ExternalLink,
  KeyRound,
  Server,
  PencilLine,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { awsConnectionService, type AWSConnection, type STSConnectResult } from "@/services/awsConnectionService";

type OnboardingStep = 1 | 2 | 3 | 4;

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

  // Onboarding wizard state
  const [onboardingStep, setOnboardingStep] = useState<OnboardingStep>(1);
  const [createdConnectionId, setCreatedConnectionId] = useState<number | null>(null);
  const [createdConnection, setCreatedConnection] = useState<AWSConnection | null>(null);
  const [formValues, setFormValues] = useState({
    aws_account_id: "",
    aws_region: "us-east-1",
  });
  const [roleArnInput, setRoleArnInput] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Action results for existing connections
  const [activeResults, setActiveResults] = useState<Record<number, any>>({});
  const [loadingAction, setLoadingAction] = useState<Record<string, boolean>>({});

  // Inline Role ARN editing state
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);
  const [inlineRoleArn, setInlineRoleArn] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const awsConnectionsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  // Step 1: Create connection record
  const createMutation = useMutation({
    mutationFn: () =>
      awsConnectionService.create({
        aws_account_id: formValues.aws_account_id,
        aws_region: formValues.aws_region,
      }),
    onSuccess: (data) => {
      setCreatedConnectionId(data.id);
      setCreatedConnection(data);
      setOnboardingStep(2);
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create AWS connection.");
    },
  });

  // Step 3: Register Role ARN
  const registerRoleArnMutation = useMutation({
    mutationFn: (connectionId: number) => awsConnectionService.registerRoleArn(connectionId, roleArnInput),
    onSuccess: (data) => {
      setCreatedConnection(data);
      setOnboardingStep(4);
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    },
    onError: (error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Invalid Role ARN format.");
    },
  });

  // Step 4: Test STS connection
  const handleTestConnection = async (id: number) => {
    const connection = awsConnectionsQuery.data?.find(c => c.id === id);
    if (!connection?.role_arn) {
      setErrorMessage("Role ARN is not set. Click the pencil icon on the Role ARN field to register it before testing the connection.");
      return;
    }
    const key = `test-${id}`;
    setLoadingAction((prev) => ({ ...prev, [key]: true }));
    setErrorMessage(null);
    try {
      const res = await awsConnectionService.connect(id);
      setActiveResults((prev) => ({ ...prev, [id]: { type: "test", data: res } }));
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err.message || "Connection test failed.";
      setActiveResults((prev) => ({ ...prev, [id]: { type: "error", message: msg } }));
      setErrorMessage(msg);
    } finally {
      setLoadingAction((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleValidatePermissions = async (id: number) => {
    const connection = awsConnectionsQuery.data?.find(c => c.id === id);
    if (!connection?.role_arn) {
      setErrorMessage("Role ARN is not set. Click the pencil icon on the Role ARN field to register it before validating permissions.");
      return;
    }
    const key = `validate-${id}`;
    setLoadingAction((prev) => ({ ...prev, [key]: true }));
    setErrorMessage(null);
    try {
      const res = await awsConnectionService.validate(id);
      setActiveResults((prev) => ({ ...prev, [id]: { type: "validate", data: res } }));
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err.message || "Validation failed.";
      setActiveResults((prev) => ({ ...prev, [id]: { type: "error", message: msg } }));
      setErrorMessage(msg);
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
      alert("Failed to disconnect: " + (err.message || "Unknown error"));
    } finally {
      setLoadingAction((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleDownloadCF = async (id: number) => {
    try {
      const data = await awsConnectionService.getCloudformationTemplate(id);
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(data.template, null, 2))}`;
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", jsonString);
      downloadAnchor.setAttribute("download", data.download_filename);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert("Failed to fetch template: " + (err.message || "Unknown error"));
    }
  };

  const handleInlineRegisterRoleArn = async (connectionId: number) => {
    if (!inlineRoleArn.trim()) return;
    const key = `register-${connectionId}`;
    setLoadingAction((prev) => ({ ...prev, [key]: true }));
    setErrorMessage(null);
    try {
      await awsConnectionService.registerRoleArn(connectionId, inlineRoleArn);
      setEditingRoleId(null);
      setInlineRoleArn("");
      await queryClient.invalidateQueries({ queryKey: ["aws-connections"] });
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err.message || "Invalid Role ARN.";
      setErrorMessage(msg);
    } finally {
      setLoadingAction((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleCopyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(label);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const resetWizard = () => {
    setIsFormOpen(false);
    setOnboardingStep(1);
    setCreatedConnectionId(null);
    setCreatedConnection(null);
    setFormValues({ aws_account_id: "", aws_region: "us-east-1" });
    setRoleArnInput("");
    setErrorMessage(null);
  };

  const handleStep1Submit = () => {
    setErrorMessage(null);
    createMutation.mutate();
  };

  const handleStep3Submit = () => {
    if (!createdConnectionId) return;
    setErrorMessage(null);
    registerRoleArnMutation.mutate(createdConnectionId);
  };

  const stepLabels = ["Account Details", "CloudFormation", "Register Role ARN", "STS Validation"];

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Top Banner */}
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
        <Button onClick={() => (isFormOpen ? resetWizard() : setIsFormOpen(true))} variant={isFormOpen ? "outline" : "default"}>
          {isFormOpen ? (
            <>
              <XCircle className="mr-2 h-4 w-4" />
              Close wizard
            </>
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Onboard AWS Account
            </>
          )}
        </Button>
      </div>

      {/* Onboarding Wizard */}
      {isFormOpen && (
        <Card className="border-border/70 shadow-soft overflow-hidden">
          {/* Step Indicator */}
          <div className="border-b bg-muted/30 px-6 py-4">
            <div className="flex items-center gap-2">
              {stepLabels.map((label, idx) => {
                const stepNum = (idx + 1) as OnboardingStep;
                const isActive = onboardingStep === stepNum;
                const isComplete = onboardingStep > stepNum;
                return (
                  <div key={label} className="flex items-center gap-2">
                    {idx > 0 && <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50" />}
                    <div className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium transition ${
                      isActive ? "bg-primary text-primary-foreground" :
                      isComplete ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {isComplete ? <CheckCircle2 className="h-3.5 w-3.5" /> : <span>{stepNum}</span>}
                      {label}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <CardContent className="p-6 space-y-6">
            {/* Error Display */}
            {errorMessage && (
              <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Error</p>
                  <p>{errorMessage}</p>
                </div>
              </div>
            )}

            {/* Step 1: Account Details */}
            {onboardingStep === 1 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Server className="h-5 w-5 text-primary" />
                    Enter AWS Account Details
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Provide the target AWS Account ID and region where the CloudFormation stack will be deployed.
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 max-w-lg">
                  <div className="space-y-2">
                    <Label htmlFor="aws_account_id">AWS Account ID</Label>
                    <Input
                      id="aws_account_id"
                      value={formValues.aws_account_id}
                      onChange={(event) => setFormValues((curr) => ({ ...curr, aws_account_id: event.target.value }))}
                      placeholder="123456789012"
                      maxLength={12}
                    />
                    <p className="text-xs text-muted-foreground">12-digit AWS account number</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="aws_region">AWS Region</Label>
                    <Input
                      id="aws_region"
                      value={formValues.aws_region}
                      onChange={(event) => setFormValues((curr) => ({ ...curr, aws_region: event.target.value }))}
                      placeholder="us-east-1"
                    />
                    <p className="text-xs text-muted-foreground">Primary deployment region</p>
                  </div>
                </div>
                <Button
                  onClick={handleStep1Submit}
                  disabled={createMutation.isPending || !formValues.aws_account_id.trim() || !formValues.aws_region.trim()}
                >
                  {createMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ArrowRight className="mr-2 h-4 w-4" />
                  )}
                  {createMutation.isPending ? "Creating..." : "Continue to CloudFormation"}
                </Button>
              </div>
            )}

            {/* Step 2: Download CloudFormation */}
            {onboardingStep === 2 && createdConnection && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Download className="h-5 w-5 text-primary" />
                    Deploy CloudFormation Stack
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Download and deploy the CloudFormation template in your AWS account. This creates the IAM role that CloudBridge will assume.
                  </p>
                </div>

                {/* Connection Info Card */}
                <div className="rounded-xl border bg-muted/30 p-4 space-y-3 max-w-xl">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Connection ID</span>
                    <span className="font-mono font-medium">{createdConnection.id}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">AWS Account</span>
                    <span className="font-mono font-medium">{createdConnection.aws_account_id}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Region</span>
                    <span className="font-mono font-medium">{createdConnection.aws_region}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">External ID</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs bg-background px-2 py-1 rounded border break-all max-w-[240px]">{createdConnection.external_id}</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(createdConnection.external_id)}
                        className="text-muted-foreground hover:text-foreground transition"
                        title="Copy External ID"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-400">
                  <p className="font-medium flex items-center gap-2 mb-1">
                    <Info className="h-4 w-4" />
                    Deployment Instructions
                  </p>
                  <ol className="list-decimal ml-5 space-y-1">
                    <li>Download the CloudFormation template below</li>
                    <li>Open AWS Console &rarr; CloudFormation &rarr; Create Stack</li>
                    <li>Upload the template and create the stack</li>
                    <li>Wait for the stack status to show <strong>CREATE_COMPLETE</strong></li>
                    <li>Copy the <strong>RoleArn</strong> from the stack Outputs tab</li>
                    <li>Click "Continue" and paste the Role ARN</li>
                  </ol>
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setOnboardingStep(1)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button onClick={() => handleDownloadCF(createdConnection.id)}>
                    <Download className="mr-2 h-4 w-4" />
                    Download CloudFormation Template
                  </Button>
                  <Button variant="outline" onClick={() => setOnboardingStep(3)}>
                    Continue to Role ARN
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Register Role ARN */}
            {onboardingStep === 3 && createdConnection && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <KeyRound className="h-5 w-5 text-primary" />
                    Register Generated Role ARN
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    After deploying the CloudFormation stack, paste the Role ARN from the stack Outputs.
                  </p>
                </div>

                <div className="space-y-2 max-w-xl">
                  <Label htmlFor="role_arn">IAM Role ARN</Label>
                  <Input
                    id="role_arn"
                    value={roleArnInput}
                    onChange={(event) => setRoleArnInput(event.target.value)}
                    placeholder="arn:aws:iam::123456789012:role/CloudBridgeMigrationRole"
                  />
                  <p className="text-xs text-muted-foreground">
                    Format: arn:aws:iam::ACCOUNT_ID:role/CloudBridgeMigrationRole
                  </p>
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setOnboardingStep(2)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    onClick={handleStep3Submit}
                    disabled={registerRoleArnMutation.isPending || !roleArnInput.trim()}
                  >
                    {registerRoleArnMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <ArrowRight className="mr-2 h-4 w-4" />
                    )}
                    {registerRoleArnMutation.isPending ? "Registering..." : "Register & Continue"}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 4: STS Validation */}
            {onboardingStep === 4 && createdConnection && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-primary" />
                    Test STS Connection
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    CloudBridge will now attempt to assume the registered role using STS AssumeRole with your External ID.
                  </p>
                </div>

                {/* Connection Summary */}
                <div className="rounded-xl border bg-muted/30 p-4 space-y-3 max-w-xl">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">AWS Account</span>
                    <span className="font-mono font-medium">{createdConnection.aws_account_id}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Role ARN</span>
                    <span className="font-mono text-xs break-all max-w-[300px]">{createdConnection.role_arn || roleArnInput}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">External ID</span>
                    <span className="font-mono text-xs">{createdConnection.external_id}</span>
                  </div>
                </div>

                {/* Test Result */}
                {activeResults[createdConnection.id] && (
                  <ConnectionResultCard result={activeResults[createdConnection.id]} />
                )}

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setOnboardingStep(3)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    onClick={() => handleTestConnection(createdConnection.id)}
                    disabled={loadingAction[`test-${createdConnection.id}`]}
                  >
                    {loadingAction[`test-${createdConnection.id}`] ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {loadingAction[`test-${createdConnection.id}`] ? "Testing..." : "Run STS AssumeRole Test"}
                  </Button>
                  <Button variant="outline" onClick={resetWizard}>
                    Finish
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Global error message for Account Overview actions */}
      {errorMessage && !isFormOpen && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p>{errorMessage}</p>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-red-400 hover:text-red-600 transition">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Existing Connections List */}
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
              No AWS accounts connected yet. Use the onboarding wizard above to get started.
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
                    <p className="font-medium text-foreground mb-1">Role ARN</p>
                    {editingRoleId === connection.id ? (
                      <div className="space-y-2">
                        <Input
                          value={inlineRoleArn}
                          onChange={(e) => setInlineRoleArn(e.target.value)}
                          placeholder="arn:aws:iam::123456789012:role/CloudBridgeMigrationRole"
                          className="text-xs font-mono h-8"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleInlineRegisterRoleArn(connection.id);
                            if (e.key === "Escape") { setEditingRoleId(null); setInlineRoleArn(""); }
                          }}
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            className="h-6 text-xs px-2"
                            onClick={() => handleInlineRegisterRoleArn(connection.id)}
                            disabled={loadingAction[`register-${connection.id}`] || !inlineRoleArn.trim()}
                          >
                            {loadingAction[`register-${connection.id}`] ? (
                              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                            ) : (
                              <CheckCircle2 className="mr-1 h-3 w-3" />
                            )}
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-6 text-xs px-2"
                            onClick={() => { setEditingRoleId(null); setInlineRoleArn(""); }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start gap-1.5">
                        <p className="mt-1 break-all bg-muted/40 p-1.5 rounded font-mono flex-1">
                          {connection.role_arn || <span className="text-amber-500 italic">Not registered — click Edit to add</span>}
                        </p>
                        <button
                          onClick={() => { setEditingRoleId(connection.id); setInlineRoleArn(connection.role_arn || ""); }}
                          className="mt-1 p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition shrink-0"
                          title="Edit Role ARN"
                        >
                          <PencilLine className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-foreground mb-1">External ID</p>
                    <div className="flex items-start gap-1.5">
                      <p className="mt-1 break-all bg-muted/40 p-1.5 rounded font-mono flex-1">{connection.external_id}</p>
                      <button
                        onClick={() => handleCopyToClipboard(connection.external_id, `ext-${connection.id}`)}
                        className="mt-1 p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition shrink-0"
                        title="Copy External ID"
                      >
                        {copiedId === `ext-${connection.id}` ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {connection.last_validated_at && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    Last validated: {new Date(connection.last_validated_at).toLocaleString()}
                  </div>
                )}

                {/* Dynamic Action Response Feed */}
                {res && <ConnectionResultCard result={res} />}

                {/* Actions Bar */}
                <div className="mt-4 flex flex-wrap gap-2 border-t pt-3 justify-between">
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleTestConnection(connection.id)}
                      disabled={loadingAction[`test-${connection.id}`]}
                      variant="outline"
                      size="sm"
                    >
                      {loadingAction[`test-${connection.id}`] ? (
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin text-green-500" />
                      ) : (
                        <Play className="mr-1.5 h-3.5 w-3.5 text-green-500" />
                      )}
                      {loadingAction[`test-${connection.id}`] ? "Testing..." : "Test STS"}
                    </Button>

                    <Button
                      onClick={() => handleValidatePermissions(connection.id)}
                      disabled={loadingAction[`validate-${connection.id}`]}
                      variant="outline"
                      size="sm"
                    >
                      {loadingAction[`validate-${connection.id}`] ? (
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin text-primary" />
                      ) : (
                        <ShieldCheck className="mr-1.5 h-3.5 w-3.5 text-primary" />
                      )}
                      {loadingAction[`validate-${connection.id}`] ? "Validating..." : "Validate IAM"}
                    </Button>

                    <Button
                      onClick={() => handleDownloadCF(connection.id)}
                      variant="outline"
                      size="sm"
                    >
                      <Download className="mr-1.5 h-3.5 w-3.5" />
                      CloudFormation
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
                        onClick={() => awsConnectionService.remove(connection.id).then(() => queryClient.invalidateQueries({ queryKey: ["aws-connections"] }))}
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
  );
}

/** Reusable card for displaying connection test / validation / error results */
function ConnectionResultCard({ result }: { result: any }) {
  if (result.type === "test") {
    const data = result.data as STSConnectResult;
    const sessionAssumed = data.session_assumed && data.details?.session_assumed;
    return (
      <div className="mt-3 rounded-xl border p-4 text-xs space-y-3">
        <div className="flex items-center gap-2">
          {sessionAssumed ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          ) : (
            <XCircle className="h-5 w-5 text-red-500" />
          )}
          <span className={`font-semibold text-sm ${sessionAssumed ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
            {sessionAssumed ? "AssumeRole Test Passed" : "AssumeRole Test Failed"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          <ResultRow label="Session Assumed" value={sessionAssumed} />
          <ResultRow label="Account Verified" value={data.details?.account_verified} />
          <ResultRow label="Region Accessible" value={data.details?.region_accessible} />
          {data.details?.caller_identity?.arn && (
            <div className="col-span-2">
              <p className="text-muted-foreground">Caller Identity ARN</p>
              <p className="font-mono break-all">{data.details.caller_identity.arn}</p>
            </div>
          )}
          {data.details?.credentials_expires_at && (
            <div className="col-span-2">
              <p className="text-muted-foreground">Credentials Expire At</p>
              <p className="font-mono">{String(data.details.credentials_expires_at)}</p>
            </div>
          )}
        </div>

        {data.details?.permissions && (
          <div>
            <p className="font-medium text-foreground mb-1">IAM Permissions</p>
            <div className="grid grid-cols-2 gap-1 font-mono">
              {Object.entries(data.details.permissions).map(([perm, ok]) => (
                <div key={perm} className="flex items-center gap-1.5">
                  {ok ? (
                    <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-500" />
                  )}
                  <span className={ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-500"}>{perm}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (result.type === "validate") {
    const data = result.data;
    return (
      <div className="mt-3 rounded-xl border p-4 text-xs space-y-2">
        <p className="font-semibold text-primary flex items-center gap-1.5">
          <Info className="h-4 w-4" />
          IAM Permissions Report ({data.status})
        </p>
        <div className="grid grid-cols-2 gap-1 font-mono">
          {Object.entries(data.permissions || {}).map(([perm, ok]) => (
            <div key={perm} className="flex items-center gap-1.5">
              {ok ? (
                <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              ) : (
                <XCircle className="h-3 w-3 text-red-500" />
              )}
              <span className={ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-500"}>{perm}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (result.type === "error") {
    return (
      <div className="mt-3 rounded-xl border border-red-500/30 bg-red-500/5 p-4 text-xs">
        <p className="text-destructive font-medium flex items-center gap-1.5">
          <AlertCircle className="h-4 w-4" />
          {result.message}
        </p>
      </div>
    );
  }

  return null;
}

function ResultRow({ label, value }: { label: string; value: boolean | undefined }) {
  return (
    <div>
      <p className="text-muted-foreground">{label}</p>
      <p className={`font-medium ${value ? "text-emerald-600 dark:text-emerald-400" : "text-red-500"}`}>
        {value ? "Yes" : "No"}
      </p>
    </div>
  );
}
