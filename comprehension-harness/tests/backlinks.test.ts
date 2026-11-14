/**
 * backlinks — which token `--check` takes for a declared symbol, and where it looks for one that resolved to
 * nothing (`../backlinks.ts`).
 *
 * What is worth fencing: that the shape of a declared symbol is not one language's naming style, and that a
 * word written in a file of any language the code folders hold is seen. No project's configuration is read:
 * the module is handed one here, and the code it scans is written to a temporary folder.
 */
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { LOOKS_DECLARED, unresolvedDeclaredLooking, type BacklinkIndex, type PageEntry, type PageToken } from '../backlinks';

vi.mock('../config', () => ({ config: { docs: 'docs', pagesNamingCode: [], source: { words: ['app', 'tests'] } } }));

describe('LOOKS_DECLARED', () => {
  it.each(['Basket', 'applyDiscount', 'apply_discount', 'apply_discount_2', '_apply_discount', '__basket_id', 'MAX_ITEMS'])(
    'takes `%s` for a declared symbol', (name) => expect(LOOKS_DECLARED.test(name)).toBe(true));

  it.each(['total', 'id', '_total', '__init__', 'apply-discount', 'apply_', 'basket.total'])(
    'does not take `%s` for one', (name) => expect(LOOKS_DECLARED.test(name)).toBe(false));
});

describe('unresolvedDeclaredLooking', () => {
  let root = '';
  beforeAll(() => {
    root = mkdtempSync(join(tmpdir(), 'comprehension-backlinks-'));
    const write = (file: string, text: string) => {
      mkdirSync(dirname(join(root, file)), { recursive: true });
      writeFileSync(join(root, file), text);
    };
    write('app/pricing.py', 'def apply_discount(basket):\n    return basket.total * RATE_OF_DISCOUNT\n');
    write('app/basket.ts', 'export const emptyBasket = () => [];\n');
    write('tests/test_pricing.py', 'def test_a_discount():\n    assert apply_discount(basket) == 9\n');
    write('elsewhere/notes.py', 'renamed_helper = None\n');
  });
  afterAll(() => rmSync(root, { recursive: true, force: true }));

  const symbol = (name: string, key: string | null = null): PageToken => ({ raw: name, name, shape: 'symbol', key, at: null });
  const indexOf = (...tokens: PageToken[]): BacklinkIndex => {
    const entry: PageEntry = { kind: 'convention', page: 'docs/conventions.md', title: 'Pricing', lead: 'Pricing', line: 3, tokens, keys: new Set() };
    return { entries: [entry], byKey: new Map() };
  };
  const found = (...tokens: PageToken[]) => unresolvedDeclaredLooking(indexOf(...tokens), root).map((u) => [u.token.name, u.appearsIn]);

  it('says in which code folders a word still appears, whatever language the file is written in', () => {
    expect(found(symbol('apply_discount'), symbol('RATE_OF_DISCOUNT'), symbol('emptyBasket'))).toEqual([
      ['apply_discount', ['app', 'tests']],
      ['RATE_OF_DISCOUNT', ['app']],
      ['emptyBasket', ['app']],
    ]);
  });

  it('lists a word no code folder holds as appearing nowhere', () => {
    expect(found(symbol('renamed_helper'), symbol('removedHelper'))).toEqual([['renamed_helper', []], ['removedHelper', []]]);
  });

  it('leaves out a token that resolved, one that is not shaped like a declared symbol, and a second mention in the entry', () => {
    expect(found(symbol('apply_discount', 'app/pricing.py#apply_discount'), symbol('total'), symbol('renamed_helper'), symbol('renamed_helper')))
      .toEqual([['renamed_helper', []]]);
  });
});
