import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { api } from "../api/client";
import { Notice, PageTitle } from "../components/ui";
import type { Application, Status } from "../types";
import { date } from "../utils/format";
const statuses: Status[] = [
  "SAVED",
  "APPLIED",
  "INTERVIEW",
  "OFFER",
  "REJECTED",
  "WITHDRAWN",
];
function ApplicationCard({ item }: { item: Application }) {
  const cache = useQueryClient();
  const change = useMutation({
    mutationFn: (body: { status: Status; notes: string }) =>
      api(`/api/applications/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["applications"] });
    },
  });
  return (
    <article className="panel application-card">
      <div className="application-head">
        <div>
          <span className="company-name">{item.job.company}</span>
          <h3>
            <Link to={`/jobs/${item.job.id}`}>{item.job.title}</Link>
          </h3>
          <p className="muted">{item.job.location}</p>
        </div>
        <span className={`chip ${item.status === "OFFER" ? "green" : ""}`}>
          {item.status}
        </span>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const values = new FormData(event.currentTarget);
          change.mutate({
            status: String(values.get("status")) as Status,
            notes: String(values.get("notes") ?? ""),
          });
        }}
      >
        <div className="form-grid">
          <label>
            Status
            <select name="status" defaultValue={item.status}>
              {statuses.map((status) => (
                <option key={status}>{status}</option>
              ))}
            </select>
          </label>
          <label>
            Notes
            <input
              name="notes"
              placeholder="A reminder, a contact, a next step…"
              maxLength={5000}
              defaultValue={item.notes}
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="button secondary" disabled={change.isPending}>
            Update application
          </button>
          {item.job.apply_url && (
            <a
              className="text-link"
              href={item.job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Official application <ArrowUpRight size={15} />
            </a>
          )}
        </div>
        <Notice error={change.error} />
      </form>
      <details>
        <summary>Activity history · {item.history.length} updates</summary>
        <ol className="history">
          {item.history.map((entry, index) => (
            <li key={index}>
              <strong>{entry.status}</strong> · {date(entry.changed_at)}
              {entry.notes && <p>{entry.notes}</p>}
            </li>
          ))}
        </ol>
      </details>
    </article>
  );
}
export function ApplicationsPage() {
  const result = useQuery({
    queryKey: ["applications"],
    queryFn: () => api<Application[]>("/api/applications"),
  });
  return (
    <>
      <PageTitle
        eyebrow="ONE STEP AT A TIME"
        title="Your application journey"
        description="Save an opportunity, apply on the official site, then keep your progress up to date."
      />
      <div className="funnel">
        {statuses.map((status) => (
          <div key={status}>
            <strong>
              {result.data?.filter((a) => a.status === status).length ?? "—"}
            </strong>
            <span>{status}</span>
          </div>
        ))}
      </div>
      <Notice
        pending={result.isPending}
        error={result.error}
        empty={result.data?.length === 0}
      >
        Save a job from Discover to begin your application journey.
      </Notice>
      <div className="application-list">
        {result.data?.map((item) => (
          <ApplicationCard key={`${item.id}-${item.updated_at}`} item={item} />
        ))}
      </div>
    </>
  );
}
