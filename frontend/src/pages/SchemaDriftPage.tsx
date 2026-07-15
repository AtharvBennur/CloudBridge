import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { GitCompare, AlertTriangle, CheckCircle2, Clock, Database, Plus, Camera } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { schemaDriftService } from "@/services/schemaDriftService";

export function SchemaDriftPage() {
  const driftEventsQuery = useQuery({
    queryKey: ["drift-events"],
    queryFn: () => schemaDriftService.listDriftEvents(1), // TODO: Get from route params
  });

  const handleApprove = async (eventId: number) => {
    try {
      await schemaDriftService.approveDriftEvent(eventId, "user");
      driftEventsQuery.refetch();
    } catch (error) {
      console.error("Failed to approve drift event:", error);
    }
  };

  const handleReject = async (eventId: number) => {
    try {
      await schemaDriftService.rejectDriftEvent(eventId, "Rejected by user", "user");
      driftEventsQuery.refetch();
    } catch (error) {
      console.error("Failed to reject drift event:", error);
    }
  };

  const handleIgnore = async (eventId: number) => {
    try {
      await schemaDriftService.ignoreDriftEvent(eventId);
      driftEventsQuery.refetch();
    } catch (error) {
      console.error("Failed to ignore drift event:", error);
    }
  };

  const events = driftEventsQuery.data || [];
  const totalChanges = events.length;
  const pendingApproval = events.filter(e => e.status === "PENDING").length;
  const autoApplied = events.filter(e => e.status === "AUTO_APPLIED").length;
  const rejected = events.filter(e => e.status === "REJECTED").length;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-orange-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 p-3 text-white shadow-lg">
            <GitCompare className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">Schema Drift Detection</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Monitor and detect schema changes in real-time with automatic drift analysis and approval workflows.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Camera className="mr-2 h-4 w-4" />
              Capture Snapshot
            </Button>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Compare Schemas
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Total Changes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">{totalChanges}</div>
            <p className="text-xs text-muted-foreground mt-1">Detected changes</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending Approval</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">{pendingApproval}</div>
            <p className="text-xs text-muted-foreground mt-1">Awaiting review</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Auto-Applied</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">{autoApplied}</div>
            <p className="text-xs text-muted-foreground mt-1">Safe changes</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Rejected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">{rejected}</div>
            <p className="text-xs text-muted-foreground mt-1">Blocked changes</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Recent Schema Changes</CardTitle>
          <CardDescription>Latest detected schema drift events requiring attention</CardDescription>
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
            {!driftEventsQuery.isLoading && events.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No schema drift detected. Compare schema snapshots to detect changes.
              </div>
            )}
            {!driftEventsQuery.isLoading && events.slice(0, 10).map((event) => (
              <div key={event.id} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    event.risk_level === "SAFE" ? "bg-emerald-500/10 text-emerald-600" :
                    event.risk_level === "MODERATE" ? "bg-orange-500/10 text-orange-600" :
                    event.risk_level === "HIGH" ? "bg-red-500/10 text-red-600" :
                    "bg-purple-500/10 text-purple-600"
                  }`}>
                    <Database className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{event.change_type.replace('_', ' ')}</h4>
                    <p className="text-sm text-muted-foreground">
                      Table: {event.table_name} {event.column_name ? `• ${event.column_name}` : ''} {event.index_name ? `• ${event.index_name}` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={event.risk_level === "SAFE" ? "success" : event.risk_level === "HIGH" ? "destructive" : "warning"}>
                    {event.risk_level}
                  </Badge>
                  <Badge variant={event.status === "APPROVED" || event.status === "AUTO_APPLIED" ? "success" : event.status === "REJECTED" ? "destructive" : "secondary"}>
                    {event.status}
                  </Badge>
                  {event.status === "PENDING" && (
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleApprove(event.id)}>Approve</Button>
                      <Button variant="ghost" size="sm" onClick={() => handleReject(event.id)}>Reject</Button>
                      <Button variant="ghost" size="sm" onClick={() => handleIgnore(event.id)}>Ignore</Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
