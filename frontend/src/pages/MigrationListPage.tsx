import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus, Trash2, PencilLine, Eye, DatabaseZap } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

import { ConfirmDeleteDialog } from "@/components/migrations/ConfirmDeleteDialog";
import { StatusBadge } from "@/components/migrations/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { migrationService, type MigrationJob } from "@/services/migrationService";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export function MigrationListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedMigrationId, setSelectedMigrationId] = useState<number | null>(null);

  const migrationsQuery = useQuery({
    queryKey: ["migrations"],
    queryFn: () => migrationService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => migrationService.remove(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["migrations"] });
      await queryClient.invalidateQueries({ queryKey: ["migration"] });
      setSelectedMigrationId(null);
    },
  });

  const sortedMigrations = useMemo(() => {
    if (!migrationsQuery.data) return [];
    return [...migrationsQuery.data].sort((a, b) => b.id - a.id);
  }, [migrationsQuery.data]);

  const columns: Column<MigrationJob>[] = [
    {
      key: "job_name",
      header: "Job Name",
      accessor: (row) => <span className="font-semibold text-foreground">{row.job_name}</span>,
    },
    {
      key: "source_database",
      header: "Source",
      accessor: (row) => <span className="text-muted-foreground">{row.source_database}</span>,
    },
    {
      key: "destination_database",
      header: "Destination",
      accessor: (row) => (
        <span className="text-muted-foreground flex items-center gap-1">
          {row.destination_database}
          <ArrowRight className="h-3 w-3" />
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      accessor: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "created_at",
      header: "Created",
      accessor: (row) => <span className="text-muted-foreground text-xs">{formatDate(row.created_at)}</span>,
    },
  ];

  const handleDelete = () => {
    if (selectedMigrationId === null) return;
    deleteMutation.mutate(selectedMigrationId);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/80 p-6 shadow-sm md:flex-row md:items-center md:justify-between"
      >
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <DatabaseZap className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold">Migration Jobs</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Review and manage metadata for every workflow in your migration catalog.
            </p>
          </div>
        </div>

        <Button onClick={() => navigate("/migrations/new")}>
          <Plus className="h-4 w-4" />
          New Migration
        </Button>
      </motion.div>

      <DataTable
        data={sortedMigrations}
        columns={columns}
        keyField="id"
        searchPlaceholder="Search migrations..."
        pageSize={10}
        isLoading={migrationsQuery.isLoading}
        emptyMessage="No migration jobs yet. Create the first one to get started."
        bulkActions={[
          {
            label: "Delete Selected",
            icon: <Trash2 className="h-3.5 w-3.5" />,
            variant: "destructive",
            onClick: (selected) => {
              if (selected.length === 1) setSelectedMigrationId(selected[0].id);
            },
          },
        ]}
        renderRowActions={(row) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="sm" onClick={() => navigate(`/migrations/${row.id}`)}>
              <Eye className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => navigate(`/migrations/${row.id}/edit`)}>
              <PencilLine className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedMigrationId(row.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      />

      <ConfirmDeleteDialog
        open={selectedMigrationId !== null}
        title="Delete migration job"
        description="This action will remove the migration job from the backend catalog."
        isDeleting={deleteMutation.isPending}
        onCancel={() => setSelectedMigrationId(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
