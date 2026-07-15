import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ShieldCheck, CheckCircle2, XCircle, Clock, AlertTriangle, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { schemaDriftService } from "@/services/schemaDriftService";
import { approvalService } from "@/services/approvalService";

export function ApprovalsPage() {
  const driftEventsQuery = useQuery({
    queryKey: ["drift-events-pending"],
    queryFn: () => schemaDriftService.listDriftEvents(1, "PENDING"),
  });

  const approvalSummaryQuery = useQuery({
    queryKey: ["approval-summary"],
    queryFn: () => approvalService.getApprovalSummary(1),
  });

  const handleApprove = async (eventId: number) => {
    try {
      await schemaDriftService.approveDriftEvent(eventId, "user");
      driftEventsQuery.refetch();
      approvalSummaryQuery.refetch();
    } catch (error) {
      console.error("Failed to approve:", error);
    }
  };

  const handleReject = async (eventId: number) => {
    try {
      await schemaDriftService.rejectDriftEvent(eventId, "Rejected by user", "user");
      driftEventsQuery.refetch();
      approvalSummaryQuery.refetch();
    } catch (error) {
      console.error("Failed to reject:", error);
    }
  };

  const handleBulkApprove = async () => {
    try {
      await approvalService.bulkApprove(1, "MODERATE", "user");
      driftEventsQuery.refetch();
      approvalSummaryQuery.refetch();
    } catch (error) {
      console.error("Failed to bulk approve:", error);
    }
  };

  const handleAutoApply = async () => {
    try {
      await approvalService.autoApplySafe(1);
      driftEventsQuery.refetch();
      approvalSummaryQuery.refetch();
    } catch (error) {
      console.error("Failed to auto apply:", error);
    }
  };

  const pendingEvents = driftEventsQuery.data || [];
  const summary = approvalSummaryQuery.data;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-purple-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 p-3 text-white shadow-lg">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">Schema Approval Center</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Review and approve schema changes detected during migration. Safe changes are auto-applied.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleBulkApprove}>
              Bulk Approve
            </Button>
            <Button size="sm" onClick={handleAutoApply}>
              Auto-Apply Safe
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending Review</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">{summary?.pending_approval || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Awaiting approval</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Auto-Approved</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">{summary?.auto_approved || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Safe changes applied</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Rejected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">{summary?.rejected || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Changes blocked</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Pending Approvals</CardTitle>
          <CardDescription>Schema changes requiring manual review before migration can proceed</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {driftEventsQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!driftEventsQuery.isLoading && pendingEvents.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No pending approvals. All schema changes have been processed.
              </div>
            )}
            {!driftEventsQuery.isLoading && pendingEvents.map((event) => (
              <div key={event.id} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    event.risk_level === "CRITICAL" ? "bg-red-500/10 text-red-600" :
                    event.risk_level === "HIGH" ? "bg-orange-500/10 text-orange-600" :
                    "bg-yellow-500/10 text-yellow-600"
                  }`}>
                    <AlertTriangle className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{event.change_type.replace('_', ' ')}</h4>
                    <p className="text-sm text-muted-foreground">
                      {event.table_name} • {event.column_name ? `Column: ${event.column_name}` : ''} {event.index_name ? `Index: ${event.index_name}` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={event.risk_level === "CRITICAL" ? "destructive" : event.risk_level === "HIGH" ? "warning" : "secondary"}>
                    {event.risk_level}
                  </Badge>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">{new Date(event.detected_at).toLocaleString()}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50" onClick={() => handleApprove(event.id)}>
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Approve
                    </Button>
                    <Button variant="outline" size="sm" className="text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => handleReject(event.id)}>
                      <XCircle className="mr-2 h-4 w-4" />
                      Reject
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
