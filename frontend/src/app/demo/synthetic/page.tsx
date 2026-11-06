import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';
import { SyntheticDemoWorkspace } from '@/components/SyntheticDemoWorkspace';

export const metadata: Metadata = {
  title: 'PracticaMIA — fictional end-to-end demonstration',
  description: 'Synthetic browser-only demonstration with no legal advice or submission.',
  robots: { index: false, follow: false },
};

export default function SyntheticDemoPage() {
  if (!syntheticDemoAvailable(process.env)) notFound();
  return <SyntheticDemoWorkspace />;
}
