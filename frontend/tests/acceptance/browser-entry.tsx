/** Synthetic browser acceptance mount of the REAL saved-case components.
 * This test-only entry is NOT a Next.js route, production feature flag, or
 * authentication workaround. The test server supplies temporary RS256 tokens.
 */
import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {DemoProvider,useDemo} from '@/components/DemoProvider';
import {SavedCasesView} from '@/components/SavedCasesView';
import {SavedCaseWorkspace} from '@/components/SavedCaseWorkspace';

function LanguageSwitch(){
  const {locale,toggleLocale}=useDemo();
  return <button type="button" onClick={toggleLocale}
    aria-label="Toggle language" style={{
      margin:12,padding:8,border:'1px solid #cbd6dc',borderRadius:6,
    }}>Language: {locale.toUpperCase()}</button>;
}

function AcceptanceApp(){
  const [path,setPath]=useState(window.location.pathname);
  useEffect(()=>{
    const update=()=>setPath(window.location.pathname);
    window.addEventListener('popstate',update);
    return ()=>window.removeEventListener('popstate',update);
  },[]);
  const id=/^\/cases\/([0-9a-f]{8}-[0-9a-f-]{27,})$/i.exec(path)?.[1];
  return <DemoProvider>
    <header><LanguageSwitch/></header>
    {id?<SavedCaseWorkspace key={id} caseId={id}
      configured={true} signedIn={true}
      assistantEnabled={false} preparationEnabled={false}
      liveAIEnabled={false} privateDocumentsEnabled={false}/>:
      <SavedCasesView key={path} configured={true} signedIn={true}
        backendConfigured={true} liveAIEnabled={false}/>}
  </DemoProvider>;
}

const root=document.getElementById('root');
if(!root) throw new Error('Local browser acceptance fixture is missing its root');
createRoot(root).render(<AcceptanceApp/>);
