import { describe, expect, it } from 'vitest';
import { rowsToCsv } from './exportCsv';

describe('rowsToCsv', () => {
  it('exports rows without internal grid ids', () => {
    expect(
      rowsToCsv([
        { __row_id: 0, name: 'Alice', city: 'NYC' },
        { __row_id: 1, name: 'Bob', city: 'LA' },
      ])
    ).toBe('name,city\nAlice,NYC\nBob,LA');
  });

  it('escapes commas, quotes, and newlines', () => {
    expect(rowsToCsv([{ name: 'Alice, Jr.', note: 'Says "hi"\nagain' }])).toBe(
      'name,note\n"Alice, Jr.","Says ""hi""\nagain"'
    );
  });

  it('neutralizes spreadsheet formula injection values', () => {
    expect(
      rowsToCsv([
        { name: '=cmd', plus: '+cmd', minus: '-cmd', at: '@cmd', safe: 'plain' },
      ])
    ).toBe("name,plus,minus,at,safe\n'=cmd,'+cmd,'-cmd,'@cmd,plain");
  });
});
