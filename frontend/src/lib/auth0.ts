import 'server-only';
import { Auth0Client } from '@auth0/nextjs-auth0/server';
import { hasAuthConfiguration } from '@/lib/auth-configuration.js';

/** Never initialize a partly configured provider or expose an API access token to JS. */
export const auth0 = hasAuthConfiguration(process.env)
  ? new Auth0Client({
      authorizationParameters: {
        audience: process.env.AUTH0_AUDIENCE,
        scope: 'openid profile email offline_access',
      },
      enableAccessTokenEndpoint: false,
      signInReturnToPath: '/account',
    })
  : null;
