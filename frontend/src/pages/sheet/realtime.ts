import type { CommittedCellUpdate } from './types';

export function formatCommittedCellUpdateToast(
  update: CommittedCellUpdate,
  currentUserId?: number
) {
  if (update.user_id !== undefined && update.user_id === currentUserId) {
    return null;
  }

  const collaborator = update.username?.trim() || 'A collaborator';
  const rowNumber = update.row_index + 1;

  return `${collaborator} updated ${update.column} on row ${rowNumber}.`;
}
