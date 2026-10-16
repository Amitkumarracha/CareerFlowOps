import type { ReactNode } from "react";
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Notice({
  error,
  pending,
  empty,
  children,
  retry,
}: {
  error?: Error | null;
  pending?: boolean;
  empty?: boolean;
  children?: ReactNode;
  retry?: () => void;
}) {
  if (pending)
    return (
      <div className="notice" role="status">
        <span className="loader" />
        Loading your workspace…
      </div>
    );
  if (error)
    return (
      <div className="notice error" role="alert">
        <p>{error.message}</p>
        {retry && (
          <button className="button secondary" onClick={retry}>
            Try again
          </button>
        )}
      </div>
    );
  if (empty)
    return (
      <div className="notice">
        <h3>Nothing here yet</h3>
        <p>
          {children ??
            "Try a broader search or ask your administrator to refresh the official sources."}
        </p>
      </div>
    );
  return null;
}
export function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <div className="metric">
      <p className="muted">{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
