'use client';

import Link from 'next/link';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';

export function Brand() {
  return <Link href="/" className="brand" aria-label="PracticaMIA"><span className="brand-mark">P<span>.</span></span><span className="brand-name">practica<span>mia</span></span></Link>;
}

export function SiteHeader({ signedIn, accountName }: { signedIn: boolean; accountName?: string }) {
  const { locale, toggleLocale, t } = useDemo();
  return <><a className="skip-link" href="#main-content">{t.skipToMain}</a><header className="site-header">
    <div className="container header-inner">
      <Brand />
      <nav className="header-nav" aria-label={locale === 'it' ? 'Navigazione principale' : 'Main navigation'}>
        <Link href="/#how-it-works" className="nav-link">{t.navHow}</Link>
        <Link href="/cases/saved" className="nav-link">{t.navStart}</Link>
        <Link href="/account" className="nav-link nav-account">
          <span>{signedIn ? accountName || t.navAccount : t.navSignIn}</span>
        </Link>
        <button type="button" className="language-toggle" onClick={toggleLocale} aria-label={locale === 'en' ? 'Switch to Italian' : 'Passa alla lingua inglese'}><Icon name="globe" size={16}/><span>{locale.toUpperCase()}</span></button>
      </nav>
    </div>
  </header></>;
}
