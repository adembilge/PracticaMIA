import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { deleteAccount } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { supabase } from "../lib/supabase";

export function AccountPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDialogElement>(null);

  async function handleDelete() {
    await deleteAccount();
    await supabase.auth.signOut();
    dialogRef.current?.close();
    navigate("/");
  }

  return (
    <section>
      <p>
        <button type="button" onClick={() => dialogRef.current?.showModal()}>
          {t("deleteAccount")}
        </button>
      </p>
      <dialog ref={dialogRef}>
        <p>{t("deleteConfirm")}</p>
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