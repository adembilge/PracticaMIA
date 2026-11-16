import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';
import { SyntheticDemoWorkspace } from '@/components/SyntheticDemoWorkspace';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'PracticaMIA — Explore a fictional case',
  description: 'Explore the steps of preparing a case, from questions to final review.',
  robots: { index: false, follow: false },
};

export default async function SyntheticDemoPage({
  searchParams,
}: { searchParams: Promise<{ step?: string | string[] }> }) {
  if (!syntheticDemoAvailable(process.env)) notFound();
  const { step } = await searchParams;
  return <SyntheticDemoWorkspace startAtDocument={step === 'document'} />;
}
