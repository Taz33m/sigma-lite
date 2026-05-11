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

  it('uses source row identity when the API provides it', () => {
    const rows = buildDatasetGridRows([
      { __source_index: 15, id: 42, name: 'Alice' },
      { __source_index: 31, id: 42, name: 'Bob' },
    ]);

    expect(rows.map((row) => row.__row_id)).toEqual([15, 31]);
  });
});
