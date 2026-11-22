import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'PracticaMIA — Administrative help, in one conversation',
  description: 'Independent English–Italian administrative assistance. Not a government service.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
