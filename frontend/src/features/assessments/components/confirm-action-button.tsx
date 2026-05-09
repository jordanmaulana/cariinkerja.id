import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Action } from "@/features/assessments/actions";

type Props = {
  action: Action;
  disabled: boolean;
  onConfirm: () => void;
};

export function ConfirmActionButton({ action, disabled, onConfirm }: Props) {
  const [open, setOpen] = useState(false);
  if (!action.confirm) return null;
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        size="xs"
        variant={action.variant ?? "default"}
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        {action.label}
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{action.confirm.title}</DialogTitle>
          <DialogDescription>{action.confirm.description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">
              Batal
            </Button>
          </DialogClose>
          <Button
            type="button"
            variant={action.variant ?? "default"}
            onClick={() => {
              setOpen(false);
              onConfirm();
            }}
          >
            {action.confirm.confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
