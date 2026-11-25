import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteAccount } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

export function AccountPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleteError(null);
    try {
      await deleteAccount();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Request failed");
      return;
    }
    await supabase.auth.signOut();
    dialogRef.current?.close();
    navigate("/");
  }

  return (
    <section>
      <p>
        <button
          type="button"
          onClick={() => {
            setDeleteError(null);
            dialogRef.current?.showModal();
          }}
        >
          {t("deleteAccount")}
        </button>
      </p>
      <dialog ref={dialogRef} onClose={() => setDeleteError(null)}>
        <p>{t("deleteConfirm")}</p>
        {deleteError ? <p role="alert">{deleteError}</p> : null}
        <p>
          <button type="button" onClick={() => dialogRef.current?.close()}>
            {t("cancel")}
          </button>
          <button type="button" onClick={() => void handleDelete()}>
            {t("deleteAccount")}
          </button>
        </p>
      </dialog>
    </section>
  );
}