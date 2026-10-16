import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshCw, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageTitle, Notice, Metric } from "../components/ui";
import type { IngestionRun } from "../types";
import { date } from "../utils/format";
interface NamedCount {
  name: string;
  count: number;
}
interface Analytics {
  scope: string;
  active_students: number;
  active_opportunities: number;
  new_jobs_today: number;
  applications: number;
  interviews: number;
  offers: number;
  top_companies: NamedCount[];
  top_job_categories: NamedCount[];
  skill_gaps: NamedCount[];
  placement_funnel: Record<string, number>;
  job_matches: {
    job_id: string;
    title: string;
    potentially_matched_candidates: number;
    eligibility_unknown_candidates: number;
  }[];
}
function Bars({ items, empty }: { items: NamedCount[]; empty: string }) {
  const max = Math.max(...items.map((i) => i.count), 1);
  return items.length ? (
    <div className="bar-list">
      {items.map((item) => (
        <div key={item.name}>
          <div>
            <span>{item.name}</span>
            <strong>{item.count}</strong>
          </div>
          <div className="bar-track">
            <span style={{ width: `${(item.count / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  ) : (
    <p className="muted">{empty}</p>
  );
}
export function TpoPage() {
  const result = useQuery({
    queryKey: ["tpo"],
    queryFn: () => api<Analytics>("/api/tpo", {}, "admin"),
  });
  const data = result.data;
  return (
    <>
      <PageTitle
        eyebrow="A WIDER VIEW OF PROGRESS"
        title="Placement intelligence"
        description="Aggregate opportunity and application insights, with candidate privacy built in."
      />
      <Notice
        pending={result.isPending}
        error={result.error}
        retry={() => void result.refetch()}
      />
      {data && (
        <>
          <div className="metrics">
            <Metric
              label="Active students"
              value={data.active_students}
              detail="Candidates with profiles"
            />
            <Metric
              label="Active opportunities"
              value={data.active_opportunities}
              detail={`${data.new_jobs_today} first seen today`}
            />
            <Metric
              label="Applications"
              value={data.applications}
              detail={`${data.interviews} interviews · ${data.offers} offers`}
            />
          </div>
          <div className="analytics-grid">
            <section className="panel">
              <h2>Placement funnel</h2>
              <Bars
                items={Object.entries(data.placement_funnel).map(
                  ([name, count]) => ({ name, count }),
                )}
                empty="No applications yet."
              />
            </section>
            <section className="panel">
              <h2>Companies hiring</h2>
              <Bars
                items={data.top_companies}
                empty="Ingest opportunities to see companies."
              />
            </section>
            <section className="panel">
              <h2>Skills to build</h2>
              <Bars
                items={data.skill_gaps}
                empty="Add candidate skills to calculate skill gaps."
              />
            </section>
            <section className="panel">
              <h2>Opportunity categories</h2>
              <Bars
                items={data.top_job_categories}
                empty="No categories available."
              />
            </section>
          </div>
          <section className="panel">
            <h2>Potential candidate matches</h2>
            <p className="fine-print">{data.scope}</p>
            <p className="muted">
              Based on explicit skill overlap. Eligibility may be unknown; these
              counts are not guarantees.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Opportunity</th>
                    <th>Potential matches</th>
                    <th>Eligibility unknown</th>
                  </tr>
                </thead>
                <tbody>
                  {data.job_matches.map((job) => (
                    <tr key={job.job_id}>
                      <td>
                        <Link to={`/jobs/${job.job_id}`}>{job.title}</Link>
                      </td>
                      <td>{job.potentially_matched_candidates}</td>
                      <td>{job.eligibility_unknown_candidates}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
interface Evaluation {
  dataset_version: string;
  labels_description: string;
  selected_algorithm: string;
  results: {
    algorithm: string;
    split: string;
    metrics: Record<string, number>;
  }[];
}
interface Mlops {
  evaluation: Evaluation | null;
  registry: {
    model_name: string;
    version: string;
    alias: string;
    run_id: string;
  } | null;
  status_message: string;
}
export function MlopsPage() {
  const [split, setSplit] = useState("all");
  const result = useQuery({
    queryKey: ["mlops"],
    queryFn: () => api<Mlops>("/api/mlops", {}, "admin"),
  });
  return (
    <>
      <PageTitle
        eyebrow="EVIDENCE BEHIND THE ENGINE"
        title="Model experiments"
        description="Saved evaluation results, dataset versions and the model selected for inference."
      />
      <Notice
        pending={result.isPending}
        error={result.error}
        retry={() => void result.refetch()}
      />
      {result.data && (
        <>
          <div className="notice">{result.data.status_message}</div>
          {result.data.registry && (
            <section className="panel registry">
              <span className="chip green">{result.data.registry.alias}</span>
              <h2>{result.data.registry.model_name}</h2>
              <p>
                Version {result.data.registry.version} · run{" "}
                {result.data.registry.run_id}
              </p>
            </section>
          )}
          {result.data.evaluation ? (
            <section className="panel">
              <h2>Reproducible ranking comparison</h2>
              <p className="muted">
                {result.data.evaluation.labels_description}
              </p>
              <p className="fine-print">
                Dataset: {result.data.evaluation.dataset_version} · selected:{" "}
                {result.data.evaluation.selected_algorithm}
              </p>
              <div className="operation-toolbar">
                <label>
                  Evaluation split{" "}
                  <select
                    value={split}
                    onChange={(e) => setSplit(e.target.value)}
                  >
                    <option value="all">All splits</option>
                    <option value="validation">Validation (selection)</option>
                    <option value="test">Test (held out)</option>
                  </select>
                </label>
                <button
                  className="button secondary"
                  onClick={() => {
                    const url = URL.createObjectURL(
                      new Blob(
                        [JSON.stringify(result.data?.evaluation, null, 2)],
                        { type: "application/json" },
                      ),
                    );
                    const anchor = document.createElement("a");
                    anchor.href = url;
                    anchor.download = "careerflowops-evaluation.json";
                    anchor.click();
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                  }}
                >
                  Download evaluation
                </button>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Algorithm / split</th>
                      <th>Precision@5</th>
                      <th>Recall@5</th>
                      <th>NDCG@5</th>
                      <th>MRR</th>
                      <th>Latency (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.evaluation.results
                      .filter((row) => split === "all" || row.split === split)
                      .map((row) => (
                        <tr
                          className={
                            row.algorithm ===
                            result.data?.evaluation?.selected_algorithm
                              ? "selected-row"
                              : ""
                          }
                          key={`${row.algorithm}-${row.split}`}
                        >
                          <td>
                            {row.algorithm}
                            <small>{row.split}</small>
                          </td>
                          {[
                            "precision_at_5",
                            "recall_at_5",
                            "ndcg_at_5",
                            "mrr",
                            "inference_latency_ms",
                          ].map((metric) => (
                            <td key={metric}>
                              {row.metrics[metric]?.toFixed(
                                metric === "inference_latency_ms" ? 1 : 3,
                              ) ?? "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <Notice empty>
              No evaluation artifact yet. Run the documented DVC pipeline to
              produce actual measurements.
            </Notice>
          )}
        </>
      )}
    </>
  );
}
interface Dedup {
  jobs: {
    id: string;
    title: string;
    source_occurrences: number;
    sources: string[];
  }[];
  possible_duplicates: {
    left_id: string;
    right_id: string;
    similarity: number;
  }[];
  scope: string;
}
export function AdminPage() {
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["ingestion"],
    queryFn: () =>
      api<IngestionRun[]>("/api/admin/ingestion/status", {}, "admin"),
    refetchInterval: 30000,
  });
  const dedup = useQuery({
    queryKey: ["dedup"],
    queryFn: () => api<Dedup>("/api/admin/dedup", {}, "admin"),
  });
  const run = useMutation({
    mutationFn: (mode: string) =>
      api<IngestionRun>(
        "/api/admin/ingestion/run",
        { method: "POST", body: JSON.stringify({ mode }) },
        "admin",
      ),
    onSuccess: () => {
      void cache.invalidateQueries();
    },
  });
  return (
    <>
      <PageTitle
        eyebrow="THE PIPELINE, IN THE OPEN"
        title="Source health"
        description="Refresh official boards, review ingestion outcomes and inspect preserved provenance."
        action={
          <button
            className="button"
            disabled={run.isPending}
            onClick={() => run.mutate("live")}
          >
            <RefreshCw size={16} />
            {run.isPending ? "Ingesting…" : "Refresh live sources"}
          </button>
        }
      />
      <div className="notice source-notice">
        <div>
          <strong>A reliable offline demonstration</strong>
          <p>
            Load frozen real ATS responses. These records are labeled historical
            snapshots.
          </p>
        </div>
        <button
          className="button secondary"
          disabled={run.isPending}
          onClick={() => run.mutate("fixture")}
        >
          Load snapshots
        </button>
      </div>
      <Notice error={run.error} />
      {run.data && (
        <p role="status" className="notice">
          Latest refresh: {run.data.status} · {run.data.counts.normalized ?? 0}{" "}
          postings normalized. Review any source errors below.
        </p>
      )}
      <Notice
        pending={result.isPending}
        error={result.error}
        empty={result.data?.length === 0}
        retry={() => void result.refetch()}
      >
        No runs yet. Refresh live sources or load snapshots.
      </Notice>
      <div className="run-list">
        {result.data?.map((item) => (
          <section className="panel run-card" key={item.id}>
            <div>
              <span
                className={`chip ${item.status === "succeeded" ? "green" : "amber"}`}
              >
                {item.status}
              </span>
              <h3>
                {item.mode === "fixture"
                  ? "Historical source snapshots"
                  : "Live official sources"}
              </h3>
              <small>{date(item.created_at)}</small>
            </div>
            <div className="run-counts">
              <span>
                <strong>{item.counts.fetched ?? 0}</strong> fetched
              </span>
              <span>
                <strong>{item.counts.normalized ?? 0}</strong> normalized
              </span>
              <span>
                <strong>{item.counts.duplicates ?? 0}</strong> duplicates
              </span>
            </div>
            {item.errors.length > 0 && (
              <p className="inline-error">{item.errors.join(" · ")}</p>
            )}
          </section>
        ))}
      </div>
      <section className="panel">
        <h2>Deduplication & provenance</h2>
        <Notice
          pending={dedup.isPending}
          error={dedup.error}
          retry={() => void dedup.refetch()}
        />
        {dedup.data && (
          <>
            <p className="muted">{dedup.data.scope}</p>
            <p>
              {dedup.data.possible_duplicates.length} possible fuzzy pairs for
              manual review.
            </p>
            {dedup.data.possible_duplicates.length > 0 && (
              <details>
                <summary>Review possible duplicate pairs</summary>
                <ul className="history">
                  {dedup.data.possible_duplicates.map((pair) => (
                    <li key={`${pair.left_id}-${pair.right_id}`}>
                      <Link className="text-link" to={`/jobs/${pair.left_id}`}>
                        {dedup.data?.jobs.find((job) => job.id === pair.left_id)
                          ?.title ?? pair.left_id}
                      </Link>
                      {" ↔ "}
                      <Link className="text-link" to={`/jobs/${pair.right_id}`}>
                        {dedup.data?.jobs.find(
                          (job) => job.id === pair.right_id,
                        )?.title ?? pair.right_id}
                      </Link>
                      <p>
                        Title similarity: {(pair.similarity * 100).toFixed(1)}%
                        · requires manual review
                      </p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Canonical opportunity</th>
                    <th>Occurrences</th>
                    <th>Sources</th>
                  </tr>
                </thead>
                <tbody>
                  {dedup.data.jobs.map((job) => (
                    <tr key={job.id}>
                      <td>
                        <Link to={`/jobs/${job.id}`}>
                          {job.title} <ArrowUpRight size={13} />
                        </Link>
                      </td>
                      <td>{job.source_occurrences}</td>
                      <td>{job.sources.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </>
  );
}
