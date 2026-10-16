import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bookmark } from "lucide-react";
import { api } from "../api/client";
import { JobCard } from "../components/JobCard";
import { Notice, PageTitle } from "../components/ui";
import type { SavedJob } from "../types";

export function SavedPage() {
  const [search, setSearch] = useState("");
  const result = useQuery({
    queryKey: ["saved"],
    queryFn: ({ signal }) => api<SavedJob[]>("/api/saved", { signal }),
  });
  const items = result.data?.filter(({ job }) =>
    `${job.title} ${job.company} ${job.location}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageTitle
        eyebrow="KEEP YOUR OPTIONS CLOSE"
        title="Saved opportunities"
        description="Your shortlist, ready when you are. Removing a bookmark keeps your application history."
        action={
          <Link className="button secondary" to="/applications">
            Application tracker <ArrowRight size={16} />
          </Link>
        }
      />
      <div className="search-panel">
        <Bookmark size={19} aria-hidden="true" />
        <label className="search-field">
          <input
            aria-label="Search saved jobs"
            placeholder="Search your shortlist"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <span className="count-label">{result.data?.length ?? "—"} saved</span>
      </div>
      <Notice
        pending={result.isPending}
        error={result.error}
        retry={() => void result.refetch()}
        empty={items?.length === 0}
      >
        {search ? (
          "No saved opportunities match your search."
        ) : (
          <>
            Bookmark a job to keep it here.{" "}
            <Link className="text-link" to="/jobs">
              Discover jobs <ArrowRight size={14} />
            </Link>
          </>
        )}
      </Notice>
      <div className="job-grid section-space">
        {items?.map(({ job }) => (
          <JobCard job={job} key={job.id} />
        ))}
      </div>
      {(result.data?.length ?? 0) >= 1000 && (
        <p className="fine-print">Showing the latest 1,000 bookmarks.</p>
      )}
    </>
  );
}
