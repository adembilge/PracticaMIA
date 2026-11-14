/** Fully fictional browser-only walkthrough; explicitly opt in for Production. */
export function syntheticDemoAvailable(env) {
  if (env.VERCEL_ENV === 'production') return env.ENABLE_PUBLIC_SYNTHETIC_DEMO === '1';
  return env.VERCEL_ENV === 'preview' ||
    (env.NODE_ENV === 'development' && !env.VERCEL_ENV);
}
