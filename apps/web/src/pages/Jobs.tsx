import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  ArrowRight,
  ArrowUpRight,
  SlidersHorizontal,
  ShieldCheck,
  Upload,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { api } from "../api/client";
import { JobCard } from "../components/JobCard";
import { PageTitle, Notice, Metric } from "../components/ui";
import type { Job, JobList } from "../types";
import { date } from "../utils/format";
import { SaveButton } from "../components/SaveButton";
export function Overview() {
  const jobs = useQuery({
    queryKey: ["jobs", "overview"],
    queryFn: () => api<JobList>("/api/jobs?limit=6"),
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string }>("/health"),
  });
  return (
    <>
      <PageTitle
        eyebrow="A LITTLE MOMENTUM GOES A LONG WAY"
        title="Find your next chapter."
        description="Good opportunities. Clearer matches. One place to move forward."
        action={
          <Link className="button secondary" to="/profile">
            Your profile <ArrowUpRight size={16} />
          </Link>
        }
      />
      <section className="hero">
        <div className="hero-content">
          <span className="hero-kicker">
            <span /> BUILT AROUND YOUR POTENTIAL
          </span>
          <h2>
            Your skills have
            <br />
            somewhere to go.
          </h2>
          <p>
            Explore official openings, understand your fit,
            <br className="desktop-break" /> and take the next step with
            confidence.
          </p>
          <Link className="button light" to="/jobs">
            Explore opportunities <ArrowRight size={17} />
          </Link>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="hero-mini mini-one">
            <span className="mini-icon">↗</span>
            <div>
              YOUR NEXT MOVE<strong>Closer than you think</strong>
            </div>
          </div>
          <div className="hero-mini mini-two">
            <ShieldCheck size={26} />
            <div>
              OFFICIAL SOURCES<strong>A direct path to apply</strong>
            </div>
          </div>
          <span className="star star-one">✦</span>
          <span className="star star-two">✦</span>
        </div>
      </section>
      <div className="metrics">
        <Metric
          label="Open opportunities"
          value={jobs.data?.total ?? "—"}
          detail="Canonical jobs in your workspace"
        />
        <Metric
          label="Discovery sources"
          value="3"
          detail="Greenhouse · Lever · Ashby"
        />
        <Metric
          label="API connection"
          value={
            health.isPending
              ? "Checking"
              : health.error
                ? "Offline"
                : "Connected"
          }
          detail="Live service health"
        />
      </div>
      <div className="section-heading">
        <div>
          <p className="eyebrow">EXPLORE WHAT’S POSSIBLE</p>
          <h2>Opportunities worth a look</h2>
        </div>
        <Link className="text-link" to="/jobs">
          View all jobs <ArrowRight size={16} />
        </Link>
      </div>
      <Notice
        pending={jobs.isPending}
        error={jobs.error}
        empty={jobs.data?.items.length === 0}
      />
      <div className="job-grid">
        {jobs.data?.items.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
      <section className="resume-banner">
        <div className="banner-icon">
          <Upload size={25} />
        </div>
        <div>
          <h3>Make your search more personal.</h3>
          <p>Upload a resume and see the skills behind every recommendation.</p>
        </div>
        <Link to="/resume" className="button secondary">
          Add your resume <ArrowRight size={16} />
        </Link>
      </section>
    </>
  );
}
export function JobsPage() {
  const [params, setParams] = useSearchParams();
  const filters = Object.fromEntries(params);
  const rawOffset = Number(params.get("offset") ?? 0);
  const offset =
    Number.isSafeInteger(rawOffset) && rawOffset >= 0 ? rawOffset : 0;
  function setOffset(value: number) {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set("offset", String(value));
      return next;
    });
  }
  const [advanced, setAdvanced] = useState(false);
  const query = new URLSearchParams({
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    limit: "12",
    offset: String(offset),
  });
  const jobs = useQuery({
    queryKey: ["jobs", query.toString()],
    queryFn: ({ signal }) => api<JobList>(`/api/jobs?${query}`, { signal }),
  });
  function filter(name: string, value: string) {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) next.set(name, value);
        else next.delete(name);
        next.delete("offset");
        return next;
      },
      { replace: true },
    );
  }
  return (
    <>
      <PageTitle
        eyebrow="THE NEXT STEP STARTS HERE"
        title="Discover opportunities"
        description="Real openings from official employer sources. Find the one that fits."
      />
      <div className="search-panel">
        <label className="search-field">
          <Search size={19} />
          <input
            aria-label="Search jobs"
            placeholder="Job title, skills or keywords"
            value={filters.keyword ?? ""}
            onChange={(e) => filter("keyword", e.target.value)}
          />
        </label>
        <label className="location-field">
          <span>Location</span>
          <input
            aria-label="Location"
            placeholder="City or country"
            value={filters.location ?? ""}
            onChange={(e) => filter("location", e.target.value)}
          />
        </label>
        <button
          className="button secondary"
          aria-expanded={advanced}
          aria-controls="job-filters"
          onClick={() => setAdvanced(!advanced)}
        >
          <SlidersHorizontal size={16} /> Filters
        </button>
      </div>
      {advanced && (
        <div className="filter-panel" id="job-filters">
          <label>
            Source
            <select
              value={filters.source ?? ""}
              onChange={(e) => filter("source", e.target.value)}
            >
              <option value="">All sources</option>
              {["greenhouse", "lever", "ashby"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Work arrangement
            <select
              value={filters.remote ?? ""}
              onChange={(e) => filter("remote", e.target.value)}
            >
              <option value="">Any arrangement</option>
              <option value="true">Remote</option>
              <option value="false">On-site / hybrid</option>
            </select>
          </label>
          <label>
            Company
            <input
              value={filters.company ?? ""}
              onChange={(e) => filter("company", e.target.value)}
              placeholder="Company name"
            />
          </label>
          <label>
            Employment type
            <input
              value={filters.employment_type ?? ""}
              onChange={(e) => filter("employment_type", e.target.value)}
              placeholder="Full time, internship…"
            />
          </label>
          <label>
            Experience
            <select
              value={filters.experience_level ?? ""}
              onChange={(e) => filter("experience_level", e.target.value)}
            >
              <option value="">Any experience</option>
              <option value="entry">Entry / graduate</option>
              <option value="internship">Internship</option>
              <option value="senior">Senior</option>
            </select>
          </label>
          <label>
            Posted since
            <input
              type="date"
              value={filters.posted_after?.slice(0, 10) ?? ""}
              onChange={(e) =>
                filter(
                  "posted_after",
                  e.target.value ? `${e.target.value}T00:00:00Z` : "",
                )
              }
            />
          </label>
          <button
            className="text-link"
            onClick={() => {
              setParams({});
            }}
          >
            Clear filters
          </button>
        </div>
      )}
      <div className="results-heading">
        <p>
          <strong>{jobs.data?.total ?? "—"}</strong> opportunities to explore
        </p>
        <small>Newest posted first · direct official links</small>
      </div>
      <Notice
        pending={jobs.isPending}
        error={jobs.error}
        empty={jobs.data?.total === 0}
        retry={() => void jobs.refetch()}
      />
      <div className="job-grid">
        {jobs.data?.items.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
      {jobs.data && jobs.data.total > 12 && (
        <div className="pagination">
          <button
            className="button secondary"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 12))}
          >
            <ChevronLeft size={16} />
            Previous
          </button>
          <span>
            {offset + 1}–{Math.min(offset + 12, jobs.data.total)} of{" "}
            {jobs.data.total}
          </span>
          <button
            className="button secondary"
            disabled={offset + 12 >= jobs.data.total}
            onClick={() => setOffset(offset + 12)}
          >
            Next
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </>
  );
}
export function JobDetail() {
  const { id } = useParams();
  const result = useQuery({
    queryKey: ["job", id],
    queryFn: () => api<Job>(`/api/jobs/${id}`),
  });
  return (
    <>
      <Link to="/jobs" className="text-link back-link">
        <ChevronLeft size={16} />
        All opportunities
      </Link>
      <Notice pending={result.isPending} error={result.error} />
      {result.data && (
        <>
          <div className="detail-actions">
            <SaveButton jobId={result.data.id} title={result.data.title} />
            <span>Save to your shortlist</span>
          </div>
          <PageTitle
            eyebrow={result.data.company.toUpperCase()}
            title={result.data.title}
            description={`${result.data.location} · ${result.data.employment_type ?? "Type not specified"}`}
            action={
              result.data.apply_url && (
                <a
                  className="button"
                  target="_blank"
                  rel="noopener noreferrer"
                  href={result.data.apply_url}
                >
                  Review & apply <ArrowUpRight size={17} />
                </a>
              )
            }
          />
          <div className="detail-grid">
            <section className="panel">
              <h2>About the opportunity</h2>
              <p className="job-description">
                {result.data.description ||
                  "The source did not provide a description. Review the official posting."}
              </p>
              <div className="chips">
                {result.data.skills.map((skill) => (
                  <span className="chip" key={skill}>
                    {skill}
                  </span>
                ))}
              </div>
            </section>
            <aside className="panel">
              <h2>From the source</h2>
              <p className="muted">Posted: {date(result.data.posted_at)}</p>
              <p className="muted">
                First seen: {date(result.data.first_seen_at)}
              </p>
              <p className="muted">
                Last seen: {date(result.data.last_seen_at)}
              </p>
              {result.data.sources.map((s) => (
                <div
                  className="source-detail"
                  key={`${s.source_name}-${s.source_job_id}`}
                >
                  <strong>{s.source_name}</strong>
                  <span
                    className={`chip ${s.verification_status === "snapshot" ? "amber" : "green"}`}
                  >
                    {s.verification_status === "snapshot"
                      ? "Historical snapshot"
                      : "Official API"}
                  </span>
                  <p className="muted">Last seen {date(s.last_seen_at)}</p>
                  <p className="muted">Verified {date(s.verified_at)}</p>
                  <a
                    href={s.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-link"
                  >
                    View official source <ArrowUpRight size={15} />
                  </a>
                </div>
              ))}
              <p className="fine-print">
                Review requirements on the official posting. Opening Apply does
                not submit an application.
              </p>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
