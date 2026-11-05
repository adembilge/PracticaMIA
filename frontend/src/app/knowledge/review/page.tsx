import { notFound } from 'next/navigation';
import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { reviewerPreviewEnabled } from '@/lib/reviewer-preview.js';
import { MobileReviewQueue } from '@/components/MobileReviewQueue';

export const dynamic = 'force-dynamic';

export default async function KnowledgeReviewPage() {
  if (!reviewerPreviewEnabled(process.env)) notFound();
  const session = auth0 ? await auth0.getSession() : null;
  return <MobileReviewQueue
    signedIn={Boolean(session)}
    configured={Boolean(auth0 &&
      backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
  />;
}
