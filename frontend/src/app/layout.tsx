import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { DemoProvider } from '@/components/DemoProvider';
import { SiteHeader } from '@/components/SiteHeader';
import { auth0 } from '@/lib/auth0';
import './globals.css';
import './editorial.css';

export const metadata: Metadata = {
  title: 'PracticaMIA — Italian paperwork, with a plan',
  description: 'Independent English–Italian administrative case preparation in Milan. Not a government service.',
};

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const session = auth0 ? await auth0.getSession() : null;
  const accountName = [session?.user.name, session?.user.nickname]
    .map(name => typeof name === 'string' ? name.trim() : '')
    .find(name => name && !name.includes('@'));

  return <html lang="en"><body><DemoProvider>
    <SiteHeader signedIn={Boolean(session)} accountName={accountName}/>
    {children}
  </DemoProvider></body></html>;
}
