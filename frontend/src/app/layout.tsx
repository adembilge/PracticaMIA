import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { DemoProvider } from '@/components/DemoProvider';
import { SiteHeader } from '@/components/SiteHeader';
import './globals.css';

export const metadata: Metadata = {
  title: 'PracticaMIA — Italian paperwork, with a plan',
  description: 'An independent prototype for guided administrative preparation in Milan. Not a government service.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body><DemoProvider><SiteHeader />{children}</DemoProvider></body></html>;
}
