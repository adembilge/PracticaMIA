/** CI-only local navigation adapter. No Auth0 or production routing bypass. */
function navigate(href:string,replace=false){
  if(replace) window.history.replaceState({},'',href);
  else window.history.pushState({},'',href);
  window.dispatchEvent(new PopStateEvent('popstate'));
}
export function useRouter(){
  return {
    push:(href:string)=>navigate(href),
    replace:(href:string)=>navigate(href,true),
    refresh:()=>window.dispatchEvent(new PopStateEvent('popstate')),
    back:()=>window.history.back(),
    forward:()=>window.history.forward(),
    prefetch:async(_href:string)=>{},
  };
}
