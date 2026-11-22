/** Validate UUID-shaped identifiers before constructing an authenticated backend path. */
export function isUuid(value) {
  return typeof value === 'string'
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

/** Internal task identifiers currently share the UUID wire format. */
export function isTaskId(value) {
  return isUuid(value);
}
