import { redirect } from 'next/navigation';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';

export const dynamic = 'force-dynamic';

export default function LegacyCasePage() {
  redirect(syntheticDemoAvailable(process.env) ? '/demo/synthetic' : '/cases/new');
}
