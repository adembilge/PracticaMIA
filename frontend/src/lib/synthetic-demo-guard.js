/** Preview/local-only visual demonstration. No backend, data uploads or live sources. */
export function syntheticDemoAvailable(env) {
  return env.VERCEL_ENV === 'preview' ||
    (env.NODE_ENV === 'development' && !env.VERCEL_ENV);
}
