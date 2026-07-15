import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { RotateCcw, Play, SkipBack, Trash2, AlertTriangle, CheckCircle2, Clock, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { rollbackService } from "@/services/rollbackService";

export function RollbackPage() {
  const checkpointsQuery = useQuery({
    queryKey: ["checkpoints"],
    queryFn: () => rollbackService.getCheckpoints(1), // TODO: Get from route params
  });

  const recoveryOptionsQuery = useQuery({
    queryKey: ["recovery-options"],
    queryFn: () => rollbackService.getRecoveryOptions(1),
    enabled: !!checkpointsQuery.data,
  });

  const handleRollback = async (checkpointId: number) => {
    try {
      await rollbackService.rollbackToCheckpoint(1, checkpointId);
      checkpointsQuery.refetch();
      recoveryOptionsQuery.refetch();
    } catch (error) {
      console.error("Failed to rollback:", error);
    }
  };

  const handleResume = async (checkpointId?: number) => {
    try {
      await rollbackService.resumeFromCheckpoint(1, checkpointId);
      checkpointsQuery.refetch();
      recoveryOptionsQuery.refetch();
    } catch (error) {
      console.error("Failed to resume:", error);
    }
  };

  const handleRestart = async () => {
    try {
      await rollbackService.restartMigration(1);
      checkpointsQuery.refetch();
      recoveryOptionsQuery.refetch();
    } catch (error) {
      console.error("Failed to restart:", error);
    }
  };

  const handleCreateCheckpoint = async () => {
    try {
      await rollbackService.createCheckpoint({
        migration_id: 1,
        checkpoint_name: `Manual checkpoint ${new Date().toLocaleString()}`,
      });
      checkpointsQuery.refetch();
    } catch (error) {
      console.error("Failed to create checkpoint:", error);
    }
  };

  const handleDeleteCheckpoint = async (checkpointId: number) => {
    try {
      await rollbackService.deleteCheckpoint(checkpointId);
      checkpointsQuery.refetch();
    } catch (error) {
      console.error("Failed to delete checkpoint:", error);
    }
  };

  const checkpoints = checkpointsQuery.data || [];
  const recoveryOptions = recoveryOptionsQuery.data;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-amber-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 p-3 text-white shadow-lg">
            <RotateCcw className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">Rollback & Recovery</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Manage checkpoints and perform recovery operations for failed or interrupted migrations.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCreateCheckpoint}>
              <Save className="mr-2 h-4 w-4" />
              Create Checkpoint
            </Button>
            <Button variant="outline" size="sm" onClick={handleRestart}>
              <SkipBack className="mr-2 h-4 w-4" />
              Restart Migration
            </Button>
          </div>
        </div>
      </motion.div>

      {recoveryOptionsQuery.isLoading ? (
        <Card className="border-border/70 shadow-sm">
          <CardContent className="pt-6">
            <Skeleton className="h-24 w-full" />
          </CardContent>
        </Card>
      ) : recoveryOptions ? (
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle>Recovery Options</CardTitle>
            <CardDescription>Available recovery actions based on current migration state</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className={`p-4 border rounded-2xl ${recoveryOptions.can_rollback ? "border-emerald-500/50 bg-emerald-500/5" : "border-border/50 bg-muted/30"}`}>
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${recoveryOptions.can_rollback ? "bg-emerald-500/10 text-emerald-600" : "bg-gray-500/10 text-gray-600"}`}>
                    <RotateCcw className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">Rollback</h4>
                    <p className="text-sm text-muted-foreground">{recoveryOptions.can_rollback ? "Available" : "Not available"}</p>
                  </div>
                </div>
              </div>
              <div className={`p-4 border rounded-2xl ${recoveryOptions.can_resume ? "border-blue-500/50 bg-blue-500/5" : "border-border/50 bg-muted/30"}`}>
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${recoveryOptions.can_resume ? "bg-blue-500/10 text-blue-600" : "bg-gray-500/10 text-gray-600"}`}>
                    <Play className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">Resume</h4>
                    <p className="text-sm text-muted-foreground">{recoveryOptions.can_resume ? "Available" : "Not available"}</p>
                  </div>
                </div>
              </div>
              <div className={`p-4 border rounded-2xl ${recoveryOptions.can_restart ? "border-purple-500/50 bg-purple-500/5" : "border-border/50 bg-muted/30"}`}>
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${recoveryOptions.can_restart ? "bg-purple-500/10 text-purple-600" : "bg-gray-500/10 text-gray-600"}`}>
                    <SkipBack className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">Restart</h4>
                    <p className="text-sm text-muted-foreground">{recoveryOptions.can_restart ? "Available" : "Not available"}</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Available Checkpoints</CardTitle>
          <CardDescription>Restore points for rollback and resume operations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {checkpointsQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!checkpointsQuery.isLoading && checkpoints.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No checkpoints available. Create a checkpoint to enable recovery options.
              </div>
            )}
            {!checkpointsQuery.isLoading && checkpoints.map((checkpoint) => (
              <div key={checkpoint.id} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                    <Save className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{checkpoint.checkpoint_name}</h4>
                    <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                      <span>Progress: {checkpoint.progress_percent}%</span>
                      <span>Rows: {checkpoint.rows_processed.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-xs text-muted-foreground">
                    {new Date(checkpoint.created_at).toLocaleString()}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => handleRollback(checkpoint.id)}>
                      <RotateCcw className="mr-2 h-4 w-4" />
                      Rollback
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleResume(checkpoint.id)}>
                      <Play className="mr-2 h-4 w-4" />
                      Resume
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteCheckpoint(checkpoint.id)}>
                      <Trash2 className="h-4 w-4" />
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
