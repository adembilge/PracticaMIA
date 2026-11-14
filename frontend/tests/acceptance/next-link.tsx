/** CI-only replacement for Next Link in the localhost browser harness.
 * Never imported by the production application or Next.js build.
 */
import type {AnchorHTMLAttributes,MouseEvent,ReactNode} from 'react';

type Props=Omit<AnchorHTMLAttributes<HTMLAnchorElement>,'href'> & {
  href:string;children?:ReactNode;
};
export default function Link({href,children,onClick,...rest}:Props){
  function click(event:MouseEvent<HTMLAnchorElement>){
    onClick?.(event);
    if(event.defaultPrevented||event.metaKey||event.ctrlKey||
      event.shiftKey||event.altKey||event.button!==0||
      rest.target==='_blank'||!href.startsWith('/'))return;
    event.preventDefault();
    window.history.pushState({},'',href);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }
  return <a {...rest} href={href} onClick={click}>{children}</a>;
}
