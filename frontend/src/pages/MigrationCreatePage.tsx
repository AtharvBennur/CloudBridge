import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { DatabaseZap, ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MigrationWizard, type WizardValues } from "@/components/migrations/MigrationWizard";
import { useToast } from "@/components/ui/toast";
import { migrationService } from "@/services/migrationService";

export function MigrationCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const createMutation = useMutation({
    mutationFn: (values: WizardValues) =>
      migrationService.create({
        job_name: values.job_name,
        source_database: values.source_database,
        destination_database: values.destination_database,
        description: values.description || undefined,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["migrations"] });
      toast({ title: "Migration created", description: "Your migration job has been registered successfully.", variant: "success" });
      navigate("/migrations");
    },
    onError: (error: unknown) => {
      toast({
        title: "Failed to create migration",
        description: error instanceof Error ? error.message : "Unable to create migration job.",
        variant: "destructive",
      });
    },
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-soft"
      >
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <DatabaseZap className="h-6 w-6" />
          </div>
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="info">Multi-Step Wizard</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">Create Migration Job</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Configure a new database migration with our guided setup wizard.
            </p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigate("/migrations")} className="w-fit -ml-1">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to migrations
        </Button>
      </motion.div>

      <MigrationWizard
        onSubmit={(values) => createMutation.mutate(values)}
        isSubmitting={createMutation.isPending}
      />
    </div>
  );
}
