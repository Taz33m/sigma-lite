import { describe, expect, it } from 'vitest';
import { buildDatasetGridRows } from '@/lib/datasetGrid';

describe('buildDatasetGridRows', () => {
  it('keeps CSV id values separate from the DataGrid row id', () => {
    const rows = buildDatasetGridRows([
      { id: 42, name: 'Alice' },
      { id: 42, name: 'Bob' },
    ]);

    expect(rows).toEqual([
      { id: 42, name: 'Alice', __row_id: 0 },
      { id: 42, name: 'Bob', __row_id: 1 },
    ]);
  });
});
