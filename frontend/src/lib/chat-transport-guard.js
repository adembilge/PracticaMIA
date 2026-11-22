/** The chat shell is always the product UI; transport remains restricted to isolated environments. */
export function chatTransportAvailable(env) {
  return env.VERCEL_ENV === 'preview'
    || (env.NODE_ENV === 'development' && !env.VERCEL_ENV);
}

const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const thread = 'threads/' + uuid;
const run = thread + '/runs/' + uuid;
const citation = '[A-Za-z0-9_.:%-]{1,240}';

/** Deny arbitrary URL paths and internal task inventory routes. */
export function allowedChatPath(method, value) {
  if (typeof value !== 'string' || value.length > 400 ||
    value.includes('%2f') || value.includes('%2F') || value.includes('..')) return false;
  if (method === 'GET') return [
    'runs/active', 'conversations/recent',
    thread + '/history', run, run + '/events',
    run + '/sources/' + citation,
  ].some(pattern => new RegExp('^' + pattern + '$').test(value));
  if (method === 'POST') return [
    'conversations', thread + '/messages',
    run + '/questions/' + uuid + '/reply',
    run + '/proposals/' + uuid + '/decision',
    run + '/stop',
  ].some(pattern => new RegExp('^' + pattern + '$').test(value));
  return false;
}

export function allowedChatQuery(path, params) {
  const keys = [...params.keys()];
  const allowed = path === 'runs/active' || path === 'conversations/recent'
    ? ['limit', 'before_accepted_at', 'before_run_id']
    : path.endsWith('/history') ? ['limit', 'before_revision']
    : path.endsWith('/events') ? ['after_seq', 'limit']
    : path.includes('/sources/') ? ['language'] : [];
  return keys.length <= allowed.length && keys.every(key => allowed.includes(key))
    && [...params.values()].every(value => value.length <= 80);
}
