import type { Metadata } from 'next';
import Link from 'next/link';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';
import type { ReactNode } from 'react';
import { DemoProvider } from '@/components/DemoProvider';
import { SiteHeader } from '@/components/SiteHeader';
import './globals.css';

export const metadata: Metadata = {
  title: 'PracticaMIA — Italian paperwork, with a plan',
  description: 'Independent English–Italian administrative case preparation in Milan. Not a government service.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body><DemoProvider><SiteHeader />{syntheticDemoAvailable(process.env) && <div role="note"
  style={{ background: '#e7f0f3', color: '#31576b', padding: '12px 24px',
    textAlign: 'center', fontSize: 12, fontWeight: 650 }}>
  FICTIONAL DEMO ONLY — no real data or official application.{' '}
  <Link href="/demo/synthetic" style={{ textDecoration: 'underline' }}>
    Open the synthetic walkthrough
  </Link>
</div>}{children}</DemoProvider></body></html>;
}
