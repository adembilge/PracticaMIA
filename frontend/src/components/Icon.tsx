import type { ReactNode } from 'react';

const paths: Record<string, ReactNode> = {
  arrowRight: <><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></>,
  arrowLeft: <><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
  file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h6"/></>,
  info: <><circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/></>,
  globe: <><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></>,
  list: <><path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/></>,
  chevronDown: <path d="m6 9 6 6 6-6"/>,
  external: <><path d="M15 3h6v6M10 14 21 3"/><path d="M21 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h6"/></>,
  home: <><path d="m3 10 9-7 9 7v11H3Z"/><path d="M9 21v-7h6v7"/></>,
  edit: <><path d="m16 5 3 3M4 20l4-.8L20 7.2 16.8 4 4.8 16Z"/></>,
  clock: <><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></>,
  x: <path d="M18 6 6 18M6 6l12 12"/>,
  alert: <><path d="m10.3 3.6-8.5 15a1.8 1.8 0 0 0 1.6 2.7h17.2a1.8 1.8 0 0 0 1.6-2.7l-8.5-15a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/></>,
  lock: <><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></>,
  sparkle: <><path d="m12 3 1.9 6.1L20 11l-6.1 1.9L12 19l-1.9-6.1L4 11l6.1-1.9L12 3Z"/><path d="M19 17v4m-2-2h4"/></>,
};

export function Icon({ name, size = 18, className = '' }: { name: keyof typeof paths; size?: number; className?: string }) {
  return <svg aria-hidden="true" className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
