import { Bookmark } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, token } from "../api/client";
import type { SavedJob } from "../types";

export function SaveButton({ jobId, title }: { jobId: string; title: string }) {
  const cache = useQueryClient();
  const saved = useQuery({
    queryKey: ["saved"],
    queryFn: ({ signal }) => api<SavedJob[]>("/api/saved", { signal }),
    enabled: Boolean(token("candidate")),
  });
  const isSaved = saved.data?.some((entry) => entry.job.id === jobId) ?? false;
  const change = useMutation({
    mutationFn: () =>
      isSaved
        ? api(`/api/saved/${jobId}`, { method: "DELETE" })
        : api("/api/saved", {
            method: "POST",
            body: JSON.stringify({ job_id: jobId }),
          }),
    onSuccess: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["saved"] }),
        cache.invalidateQueries({ queryKey: ["applications"] }),
        cache.invalidateQueries({ queryKey: ["tpo"] }),
      ]);
    },
  });
  return (
    <div className="save-control">
      <button
        className="icon-button"
        title={isSaved ? "Remove bookmark" : "Save job"}
        aria-label={`${isSaved ? "Unsave" : "Save"} ${title}`}
        aria-pressed={isSaved}
        onClick={() => change.mutate()}
        disabled={change.isPending || saved.isFetching}
      >
        <Bookmark size={19} fill={isSaved ? "currentColor" : "none"} />
      </button>
      {change.error && (
        <p role="alert" className="save-feedback inline-error">
          {change.error.message}
        </p>
      )}
      {change.isSuccess && (
        <span role="status" className="sr-only">
          {isSaved ? "Saved to your workspace" : "Bookmark removed"}
        </span>
      )}
    </div>
  );
}
