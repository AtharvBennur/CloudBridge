import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { User, Mail, Calendar, Shield, Building2, Pencil, Check, X, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { observabilityService } from "@/services/observabilityService";

export function AccountPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(user?.displayName || "");

  const auditLogsQuery = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => observabilityService.getAuditLogs({ limit: 20 }),
  });

  const logs = auditLogsQuery.data || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Account</h1>
        <p className="text-muted-foreground mt-2">Manage your account settings and preferences</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile Information
            </CardTitle>
            <CardDescription>Your personal account details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Display Name</label>
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder="Enter display name"
                    className="flex-1"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setIsEditing(false);
                      setEditName(user?.displayName || "");
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      setIsEditing(false);
                    }}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm flex-1">{user?.displayName || "Not set"}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setEditName(user?.displayName || "");
                      setIsEditing(true);
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Email Address</label>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">{user?.email || "Not set"}</span>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Account Role</label>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">User</span>
                <Badge variant="indigo" className="ml-auto">Active</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Security
            </CardTitle>
            <CardDescription>Authentication and security settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Authentication Method</label>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Email & Password</span>
                <Badge variant="success" className="ml-auto">Active</Badge>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Account Status</label>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Authenticated</span>
                <Badge variant="success" className="ml-auto">Active</Badge>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Current Session</label>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Active now</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account Activity</CardTitle>
          <CardDescription>Recent account activity and system events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {auditLogsQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!auditLogsQuery.isLoading && logs.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No activity recorded yet.
              </div>
            )}
            {!auditLogsQuery.isLoading &&
              logs.slice(0, 10).map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-border/50"
                >
                  <div>
                    <p className="text-sm font-medium">{log.event_type}</p>
                    <p className="text-xs text-muted-foreground">
                      {log.event_description}
                      {log.user_email && ` \u2022 ${log.user_email}`}
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(log.occurred_at).toLocaleString()}
                  </span>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
