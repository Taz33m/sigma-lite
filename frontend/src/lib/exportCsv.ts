function escapeCsvValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }

  const rawText = String(value);
  const text = /^[=+\-@]/.test(rawText) ? `'${rawText}` : rawText;
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }

  return text;
}

export function rowsToCsv(rows: Record<string, unknown>[]): string {
  const columns = Array.from(
    new Set(rows.flatMap((row) => Object.keys(row).filter((key) => !key.startsWith('__'))))
  );

  if (!columns.length) {
    return '';
  }

  const header = columns.map(escapeCsvValue).join(',');
  const body = rows.map((row) =>
    columns.map((column) => escapeCsvValue(row[column])).join(',')
  );

  return [header, ...body].join('\n');
}

export function downloadCsv(rows: Record<string, unknown>[], filename: string) {
  const csv = rowsToCsv(rows);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
