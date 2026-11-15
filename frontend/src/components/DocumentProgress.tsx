export function DocumentProgress({ label }: { label: string }) {
  return (
    <div className="document-progress" role="status">
      <span className="editorial-pending">{label}</span>
      <span className="document-progress-track" aria-hidden="true" />
    </div>
  );
}
