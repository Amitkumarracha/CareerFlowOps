import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Database,
  GitBranch,
  Server,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api/client";
import { Metric, Notice, PageTitle } from "../components/ui";
import type { Readiness } from "../types";

const training = [
  [
    "Raw ATS data",
    "Official Greenhouse, Lever and Ashby responses; provenance retained.",
  ],
  [
    "DVC preprocessing",
    "Normalize, deduplicate and build the frozen evaluation dataset.",
  ],
  [
    "MLflow experiments",
    "Compare TF-IDF, SentenceTransformer and hybrid ranking on saved metrics.",
  ],
  [
    "Model selection",
    "Validation selects a run; held-out test results remain separate.",
  ],
  [
    "Model registration",
    "Promote the selected MLflow run to the production alias.",
  ],
  [
    "DVC release bundle",
    "Export the selected model, evaluation and checksummed manifest.",
  ],
];
const deployment = [
  [
    "GitHub Actions",
    "Run checks, build API/web images, publish SHA tags to ECR when configured.",
  ],
  [
    "ECR registry",
    "Store application images separately from versioned model artifacts.",
  ],
  [
    "EC2 pulls image",
    "The operator deploys images matching the checkout's Git SHA.",
  ],
  [
    "EC2 pulls model",
    "DVC downloads the release from S3; the API image validates it before startup.",
  ],
  [
    "Running API",
    "Database and model inference readiness checks; containers restart unless stopped.",
  ],
  [
    "Client prediction",
    "Your reviewed profile produces ranked jobs with explanations and model identity.",
  ],
];
function Flow({ items }: { items: string[][] }) {
  return (
    <ol className="pipeline-flow">
      {items.map(([title, description], index) => (
        <li key={title}>
          <span className="step-number">{index + 1}</span>
          <div>
            <h3>{title}</h3>
            <p>{description}</p>
          </div>
          {index < items.length - 1 && (
            <ArrowRight className="flow-arrow" size={15} />
          )}
        </li>
      ))}
    </ol>
  );
}
export function SystemPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string }>("/health"),
    refetchInterval: 30000,
  });
  const ready = useQuery({
    queryKey: ["readiness"],
    queryFn: () => api<Readiness>("/ready"),
    refetchInterval: 30000,
  });
  return (
    <>
      <PageTitle
        eyebrow="FROM DATA TO A WORKING PREDICTION"
        title="System & workspace guide"
        description="Understand the workflow, check live API readiness, and see what is required for a cloud demonstration."
        action={
          <button
            className="button secondary"
            disabled={ready.isFetching || health.isFetching}
            onClick={() => {
              void ready.refetch();
              void health.refetch();
            }}
          >
            Refresh status
          </button>
        }
      />
      <div className="metrics">
        <Metric
          label="API process"
          value={
            health.isPending
              ? "Checking"
              : health.error
                ? "Unavailable"
                : "Online"
          }
          detail="Live /health check"
        />
        <Metric
          label="Database / readiness"
          value={
            ready.isPending ? "Checking" : ready.error ? "Not ready" : "Ready"
          }
          detail="Live /ready check"
        />
        <Metric
          label="Model delivery"
          value={
            ready.data?.bundle_id
              ? "Verified bundle"
              : ready.error
                ? "Unknown"
                : "Development"
          }
          detail={
            ready.data?.model_version ??
            "Development readiness checks database only"
          }
        />
      </div>
      <Notice
        error={health.error || ready.error}
        retry={() => {
          void health.refetch();
          void ready.refetch();
        }}
      />
      {ready.data?.bundle_id && (
        <section className="panel">
          <h2>
            <ShieldCheck size={19} /> Verified release
          </h2>
          <p>
            Algorithm: {ready.data.algorithm} · version:{" "}
            {ready.data.model_version}
          </p>
          <p className="fine-print">Bundle SHA-256: {ready.data.bundle_id}</p>
          <p className="fine-print">
            File integrity, inference-code compatibility and a prediction were
            checked when this process loaded its read-only release.
          </p>
        </section>
      )}
      <section className="panel">
        <h2>Start your job search</h2>
        <div className="guide-grid">
          {[
            [
              "/resume",
              "1. Add your experience",
              "Upload a selectable-text PDF, or enter your profile manually.",
            ],
            [
              "/recommended",
              "2. Understand your matches",
              "Review component scores, missing skills and eligibility uncertainty.",
            ],
            [
              "/saved",
              "3. Build a shortlist",
              "Bookmark official openings and review employer requirements.",
            ],
            [
              "/applications",
              "4. Track your progress",
              "Apply on the employer's site, then update status and notes here.",
            ],
          ].map(([to, title, description]) => (
            <Link className="guide-card" key={to} to={to}>
              <CheckCircle2 size={20} />
              <h3>{title}</h3>
              <p>{description}</p>
              <ArrowUpRight size={16} />
            </Link>
          ))}
        </div>
      </section>
      <div className="analytics-grid">
        <section className="panel">
          <h2>
            <Database size={20} /> Data & model lifecycle
          </h2>
          <Flow items={training} />
          <Link className="text-link" to="/mlops">
            See saved experiment results <ArrowRight size={15} />
          </Link>
        </section>
        <section className="panel">
          <h2>
            <Server size={20} /> Deployment lifecycle
          </h2>
          <Flow items={deployment} />
          <p className="deployment-note">
            Deployment code is prepared. This page does not verify AWS
            provisioning, ECR publishing or EC2 hosting. Complete the AWS
            runbook and retain deployment evidence.
          </p>
        </section>
      </div>
      <section className="panel">
        <h2>
          <GitBranch size={20} /> Technology & access
        </h2>
        <div className="guide-grid">
          <div>
            <h3>Application</h3>
            <p>
              React, Vite, strict TypeScript · FastAPI, Pydantic · PostgreSQL,
              SQLAlchemy, Alembic.
            </p>
          </div>
          <div>
            <h3>ML & operations</h3>
            <p>
              scikit-learn, SentenceTransformer · DVC, MLflow · Docker, GitHub
              Actions · Prometheus, Grafana · AWS ECR, S3 and EC2.
            </p>
          </div>
        </div>
        <p className="section-space">
          Use Workspace access for your candidate or admin/TPO token. Tokens
          stay in this tab. Disconnect clears the workspace cache. This
          demonstration uses one candidate identity.
        </p>
        <p className="fine-print section-space">
          The sample benchmark uses 29 real frozen jobs and six fictional
          queries with illustrative agent-authored relevance labels. It is not
          human-validated evidence of general ranking quality. No application is
          submitted automatically.
        </p>
      </section>
    </>
  );
}
