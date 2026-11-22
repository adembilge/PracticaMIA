import {createRoot} from 'react-dom/client';
import {SingleChatWorkspace} from '@/components/SingleChatWorkspace';

declare global {
  interface Window { acceptanceSubject?: string }
}

const subject=/\bacceptance_subject=(alice|bob)\b/.exec(document.cookie)?.[1];
window.acceptanceSubject=subject;
const root=document.getElementById('root');
if(!root)throw new Error('Chat acceptance root is missing');
createRoot(root).render(
  <SingleChatWorkspace signedIn={Boolean(subject)} configured displayName="Synthetic participant"/>,
);
