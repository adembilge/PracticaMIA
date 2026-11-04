/** Server-only authentication configuration and proxy allowlist. */
export function hasAuthConfiguration(env) {
  const keys = ['AUTH0_DOMAIN', 'AUTH0_CLIENT_ID', 'AUTH0_CLIENT_SECRET', 'AUTH0_SECRET', 'AUTH0_AUDIENCE'];
  return keys.every((key) => typeof env[key] === 'string' && env[key].trim().length > 0)
    && /^[\da-fA-F]{64}$/.test(env.AUTH0_SECRET)
    && /^[a-zA-Z0-9.-]+$/.test(env.AUTH0_DOMAIN);
}

export function backendOrigin(value, nodeEnv = 'production') {
  if (!value || typeof value !== 'string') return null;
  try {
    const parsed = new URL(value);
    const localhost = ['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname);
    if (parsed.protocol !== 'https:' &&
        !(nodeEnv !== 'production' && parsed.protocol === 'http:' && localhost)) return null;
    if (parsed.username || parsed.password || parsed.search || parsed.hash ||
        parsed.pathname !== '/') return null;
    return parsed.origin;
  } catch {
    return null;
  }
}

/** Require a same-origin Origin header before mutating a saved case (CSRF). */
export function sameOrigin(requestUrl, origin) {
  if (!origin) return false;
  try {
    const destination = new URL(requestUrl);
    const supplied = new URL(origin);
    return destination.origin === supplied.origin &&
      supplied.pathname === '/' && !supplied.search && !supplied.hash;
  } catch {
    return false;
  }
}
