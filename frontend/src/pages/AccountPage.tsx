import { useRef } from "react";
import { useI18n } from "../lib/i18n";

export function AccountPage() {
  const { t } = useI18n();
  const dialogRef = useRef<HTMLDialogElement>(null);

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
          <button type="button" onClick={() => dialogRef.current?.close()}>
            {t("deleteAccount")}
          </button>
        </p>
      </dialog>
    </section>
  );
}