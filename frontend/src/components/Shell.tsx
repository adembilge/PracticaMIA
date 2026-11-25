import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { useI18n } from "../lib/i18n";
import { Sidebar } from "./Sidebar";

function useMobileSidebar() {
  const query = "(max-width: 800px)";
  const [mobile, setMobile] = useState(() => window.matchMedia(query).matches);
  const [sidebarHidden, setSidebarHidden] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => {
      setMobile(mq.matches);
      setSidebarHidden(mq.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return { mobile, sidebarHidden, setSidebarHidden };
}

export function Shell() {
  const { t } = useI18n();
  const { mobile, sidebarHidden, setSidebarHidden } = useMobileSidebar();

  return (
    <div className="shell">
      <Sidebar
        hidden={mobile && sidebarHidden}
        showClose={mobile && !sidebarHidden}
        onClose={() => setSidebarHidden(true)}
      />
      <main>
        {mobile && sidebarHidden ? (
          <p>
            <button type="button" onClick={() => setSidebarHidden(false)}>
              {t("menu")}
            </button>
          </p>
        ) : null}
        <Outlet />
      </main>
    </div>
  );
}