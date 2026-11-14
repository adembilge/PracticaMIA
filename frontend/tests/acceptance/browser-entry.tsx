/** Synthetic browser acceptance mount of the REAL saved-case components.
 * This test-only entry is NOT a Next.js route, production feature flag, or
 * authentication workaround. The test server supplies temporary RS256 tokens.
 */
import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {DemoProvider} from '@/components/DemoProvider';
import {SiteHeader} from '@/components/SiteHeader';
import {SavedCasesView} from '@/components/SavedCasesView';
import {PrivateDocumentsWorkspace} from '@/components/PrivateDocumentsWorkspace';
import {SavedCaseWorkspace} from '@/components/SavedCaseWorkspace';

declare global {
  interface Window { acceptancePrivateDocuments?: boolean }
}

function AcceptanceApp(){
  const [path,setPath]=useState(window.location.pathname);
  useEffect(()=>{
    const update=()=>setPath(window.location.pathname);
    window.addEventListener('popstate',update);
    return ()=>window.removeEventListener('popstate',update);
  },[]);
  const route=/^\/cases\/([0-9a-f]{8}-[0-9a-f-]{27,})(\/documents)?$/i.exec(path);
  const id=route?.[1];
  const documentsEnabled=Boolean(window.acceptancePrivateDocuments);
  const signedIn=/\bacceptance_subject=(alice|bob)\b/.test(document.cookie);
  return <DemoProvider>
    <SiteHeader/>
    {documentsEnabled && route?.[2] && id ?
      <PrivateDocumentsWorkspace key={id} caseId={id} configured signedIn={signedIn}/> :
      id?<SavedCaseWorkspace key={id} caseId={id}
      configured={true} signedIn={signedIn}
      assistantEnabled={false} preparationEnabled={false}
      liveAIEnabled={false} privateDocumentsEnabled={documentsEnabled}/>:
      <SavedCasesView key={path} configured={true} signedIn={signedIn}
        backendConfigured={true} liveAIEnabled={false}/>}
  </DemoProvider>;
}

const root=document.getElementById('root');
if(!root) throw new Error('Local browser acceptance fixture is missing its root');
createRoot(root).render(<AcceptanceApp/>);
