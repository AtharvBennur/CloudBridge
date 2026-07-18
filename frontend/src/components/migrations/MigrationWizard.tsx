import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  ChevronRight,
  ChevronLeft,
  Database,
  Server,
  Settings2,
  ClipboardCheck,
  Loader2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { databaseConfigService } from "@/services/databaseConfigService";
import { awsConnectionService } from "@/services/awsConnectionService";

export interface WizardValues {
  job_name: string;
  source_database: string;
  destination_database: string;
  description: string;
  chunk_size: string;
  max_retries: string;
}

interface MigrationWizardProps {
  onSubmit: (values: WizardValues) => void;
  isSubmitting: boolean;
}

const steps = [
  { id: 0, title: "Basics", icon: ClipboardCheck },
  { id: 1, title: "Source & Target", icon: Database },
  { id: 2, title: "Configuration", icon: Settings2 },
  { id: 3, title: "Review", icon: Check },
];

export function MigrationWizard({ onSubmit, isSubmitting }: MigrationWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [values, setValues] = useState<WizardValues>({
    job_name: "",
    source_database: "",
    destination_database: "",
    description: "",
    chunk_size: "1000",
    max_retries: "3",
  });

  const databasesQuery = useQuery({
    queryKey: ["database-configs"],
    queryFn: () => databaseConfigService.list(),
  });

  const awsQuery = useQuery({
    queryKey: ["aws-connections"],
    queryFn: () => awsConnectionService.list(),
  });

  const updateField = <K extends keyof WizardValues>(key: K, value: WizardValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return values.job_name.trim().length > 0;
      case 1:
        return values.source_database.trim().length > 0 && values.destination_database.trim().length > 0;
      case 2:
        return true;
      case 3:
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1 && canProceed()) {
      setCurrentStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) setCurrentStep((s) => s - 1);
  };

  const databases = databasesQuery.data || [];
  const sourceDbs = databases.filter((d) => d.purpose === "SOURCE");
  const destDbs = databases.filter((d) => d.purpose === "DESTINATION");

  return (
    <div className="space-y-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-between">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center flex-1">
            <button
              onClick={() => i < currentStep && setCurrentStep(i)}
              className={cn(
                "flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all",
                i === currentStep
                  ? "bg-primary/10 text-primary"
                  : i < currentStep
                    ? "text-emerald-600 cursor-pointer hover:bg-emerald-500/10"
                    : "text-muted-foreground cursor-default",
              )}
              disabled={i > currentStep}
            >
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-all",
                  i === currentStep
                    ? "bg-primary text-primary-foreground"
                    : i < currentStep
                      ? "bg-emerald-500 text-white"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {i < currentStep ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              <span className="hidden sm:inline">{step.title}</span>
            </button>
            {i < steps.length - 1 && (
              <div className={cn("mx-2 h-px flex-1", i < currentStep ? "bg-emerald-500/40" : "bg-border")} />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          <Card className="border-border/70 shadow-soft">
            <CardContent className="pt-6 space-y-4">
              {currentStep === 0 && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="job_name">Migration Job Name</Label>
                    <Input
                      id="job_name"
                      value={values.job_name}
                      onChange={(e) => updateField("job_name", e.target.value)}
                      placeholder="e.g. Production Data Sync Q4"
                      required
                    />
                    <p className="text-xs text-muted-foreground">Give your migration job a clear, descriptive name.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Description (Optional)</Label>
                    <textarea
                      id="description"
                      className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                      value={values.description}
                      onChange={(e) => updateField("description", e.target.value)}
                      placeholder="Notes about this migration..."
                    />
                  </div>
                </>
              )}

              {currentStep === 1 && (
                <>
                  <div className="space-y-2">
                    <Label>Source Database</Label>
                    <select
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                      value={values.source_database}
                      onChange={(e) => updateField("source_database", e.target.value)}
                    >
                      <option value="">-- Select source database --</option>
                      {sourceDbs.map((db) => (
                        <option key={db.id} value={db.name}>
                          {db.name} ({db.database_type} - {db.host})
                        </option>
                      ))}
                    </select>
                    {sourceDbs.length === 0 && (
                      <p className="text-xs text-amber-500">No source databases registered. Add one in Database Configurations.</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Destination Database</Label>
                    <select
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                      value={values.destination_database}
                      onChange={(e) => updateField("destination_database", e.target.value)}
                    >
                      <option value="">-- Select destination database --</option>
                      {destDbs.map((db) => (
                        <option key={db.id} value={db.name}>
                          {db.name} ({db.database_type} - {db.host})
                        </option>
                      ))}
                    </select>
                    {destDbs.length === 0 && (
                      <p className="text-xs text-amber-500">No destination databases registered. Add one in Database Configurations.</p>
                    )}
                  </div>
                </>
              )}

              {currentStep === 2 && (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="chunk_size">Chunk Size (rows per batch)</Label>
                      <Input
                        id="chunk_size"
                        type="number"
                        value={values.chunk_size}
                        onChange={(e) => updateField("chunk_size", e.target.value)}
                        min={100}
                        max={100000}
                      />
                      <p className="text-xs text-muted-foreground">Number of rows migrated per batch. Default: 1000</p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="max_retries">Max Retries</Label>
                      <Input
                        id="max_retries"
                        type="number"
                        value={values.max_retries}
                        onChange={(e) => updateField("max_retries", e.target.value)}
                        min={0}
                        max={10}
                      />
                      <p className="text-xs text-muted-foreground">How many times to retry on failure. Default: 3</p>
                    </div>
                  </div>
                  <div className="rounded-xl border border-border/50 bg-muted/30 p-4">
                    <h4 className="text-sm font-semibold flex items-center gap-2">
                      <Settings2 className="h-4 w-4 text-primary" />
                      Advanced Defaults
                    </h4>
                    <p className="mt-1 text-xs text-muted-foreground">
                      The migration engine will use ECS Fargate workers for execution. Checkpoints are created automatically every chunk batch for rollback safety.
                    </p>
                  </div>
                </>
              )}

              {currentStep === 3 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Review & Confirm</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <ReviewField label="Job Name" value={values.job_name} />
                    <ReviewField label="Description" value={values.description || "—"} />
                    <ReviewField label="Source Database" value={values.source_database} />
                    <ReviewField label="Destination Database" value={values.destination_database} />
                    <ReviewField label="Chunk Size" value={`${values.chunk_size} rows/batch`} />
                    <ReviewField label="Max Retries" value={values.max_retries} />
                  </div>
                  <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
                    <p className="text-sm text-primary font-medium">
                      Ready to create this migration job? Click "Create Migration" to submit.
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={handleBack}
          disabled={currentStep === 0 || isSubmitting}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back
        </Button>

        {currentStep < steps.length - 1 ? (
          <Button onClick={handleNext} disabled={!canProceed()}>
            Next
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={() => onSubmit(values)} disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Migration"
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

function ReviewField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/50 bg-muted/20 p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}
