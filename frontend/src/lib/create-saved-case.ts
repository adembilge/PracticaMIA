import { isCaseId } from '@/lib/case-scope.js';

export async function createSavedCase(): Promise<{ id: string } | { expired: true }> {
  const response = await fetch('/api/cases', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
    credentials: 'same-origin',
  });
  if (response.status === 401) return { expired: true };
  if (!response.ok) throw new Error('Could not start case');
  const created: { id?: unknown } = await response.json();
  if (typeof created?.id !== 'string' || !isCaseId(created.id)) throw new Error('Invalid case ID');
  return { id: created.id };
}
