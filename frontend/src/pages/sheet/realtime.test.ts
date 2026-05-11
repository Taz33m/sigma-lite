import { describe, expect, it } from 'vitest';
import { formatCommittedCellUpdateToast } from './realtime';

describe('formatCommittedCellUpdateToast', () => {
  const baseUpdate = {
    row_index: 2,
    column: 'city',
    value: 'Boston',
    version: 4,
  };

  it('formats collaborator, column, and display row for committed remote updates', () => {
    expect(
      formatCommittedCellUpdateToast(
        {
          ...baseUpdate,
          user_id: 7,
          username: 'Mina',
          timestamp: '2026-05-11T13:00:00Z',
        },
        3
      )
    ).toBe('Mina updated city on row 3.');
  });

  it('does not format a toast for the current user own committed update', () => {
    expect(
      formatCommittedCellUpdateToast(
        {
          ...baseUpdate,
          user_id: 7,
          username: 'Mina',
        },
        7
      )
    ).toBeNull();
  });

  it('falls back when optional broadcast identity metadata is missing', () => {
    expect(formatCommittedCellUpdateToast(baseUpdate, 7)).toBe(
      'A collaborator updated city on row 3.'
    );
  });
});
