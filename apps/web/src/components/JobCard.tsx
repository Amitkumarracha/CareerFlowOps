import {
  Bookmark,
  ArrowUpRight,
  MapPin,
  BriefcaseBusiness,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Job, Match } from "../types";
import { date, percent } from "../utils/format";
export function JobCard({ job, match }: { job: Job; match?: Match }) {
  const cache = useQueryClient();
  const save = useMutation({
    mutationFn: () =>
      api("/api/saved", {
        method: "POST",
        body: JSON.stringify({ job_id: job.id }),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["saved"] });
      void cache.invalidateQueries({ queryKey: ["applications"] });
    },
  });
  const sourceNames = [...new Set(job.sources.map((s) => s.source_name))];
  return (
    <article className="job-card">
      <div className="job-card-top">
        <div className="company-icon" aria-hidden="true">
          {job.company.slice(0, 1).toUpperCase()}
        </div>
        <div className="company-line">
          <span className="company-name">{job.company}</span>
          <span className="source">{sourceNames.join(" · ")}</span>
        </div>
        <button
          className="icon-button"
          title="Save job"
          aria-label={`Save ${job.title}`}
          onClick={() => save.mutate()}
          disabled={save.isPending || save.isSuccess}
        >
          <Bookmark size={18} fill={save.isSuccess ? "currentColor" : "none"} />
        </button>
      </div>
      <h3>
        <Link to={`/jobs/${job.id}`}>{job.title}</Link>
      </h3>
      <div className="job-meta">
        <span>
          <MapPin size={14} />
          {job.location}
        </span>
        <span>
          <BriefcaseBusiness size={14} />
          {job.employment_type ?? "Type not specified"}
        </span>
      </div>
      <div className="chips">
        {job.remote === true && <span className="chip green">Remote</span>}
        {job.experience_level && (
          <span className="chip">{job.experience_level}</span>
        )}
        {job.skills.slice(0, 3).map((skill) => (
          <span className="chip" key={skill}>
            {skill}
          </span>
        ))}
        {job.sources.every((s) => s.verification_status === "snapshot") && (
          <span className="chip amber">Source snapshot</span>
        )}
      </div>
      {match && (
        <div className="match-summary">
          <strong>{percent(match.overall_score)} match</strong>
          <p>{match.explanation[0]}</p>
          <div className="score-track">
            <span style={{ width: percent(match.overall_score) }} />
          </div>
        </div>
      )}
      <div className="job-footer">
        <small>{date(job.posted_at)}</small>
        <Link className="text-link" to={`/jobs/${job.id}`}>
          View job <ArrowUpRight size={15} />
        </Link>
        {job.apply_url && (
          <a
            className="apply-link"
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Apply <ArrowUpRight size={14} />
          </a>
        )}
      </div>
      {save.error && (
        <p role="alert" className="inline-error">
          {save.error.message}
        </p>
      )}
      {save.isSuccess && (
        <p role="status" className="success">
          Saved to your workspace
        </p>
      )}
    </article>
  );
}
