/*
Purpose:
This file renders a lightweight confirmation dialog for delete actions.

Why:
Migration deletion should be explicit and avoid accidental data loss.

Architecture:
Migration Detail/List Pages
↓
Delete Confirmation Dialog
*/

import { Button } from "@/components/ui/button";

interface ConfirmDeleteDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  isDeleting?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDeleteDialog({
  open,
  title,
  description,
  confirmLabel = "Delete",
  isDeleting = false,
  onCancel,
  onConfirm,
}: ConfirmDeleteDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-border/70 bg-background p-6 shadow-2xl">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>

        <div className="mt-6 flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" variant="destructive" onClick={onConfirm} disabled={isDeleting}>
            {isDeleting ? "Deleting" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
