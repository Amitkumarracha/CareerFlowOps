import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload, Sparkles, ArrowRight, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";
import { PageTitle, Notice } from "../components/ui";
import { JobCard } from "../components/JobCard";
import type { Match, Profile } from "../types";
import { percent } from "../utils/format";
const emptyProfile: Profile = {
  name: null,
  email: null,
  phone: null,
  location: null,
  experience_years: null,
  skills: [],
  summary: "",
  education: "",
  experience: "",
  projects: "",
  certifications: "",
};
function ProfileForm({ profile }: { profile: Profile }) {
  const cache = useQueryClient();
  const save = useMutation({
    mutationFn: (body: Profile) =>
      api<Profile>("/api/profile", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["profile"] });
      void cache.invalidateQueries({ queryKey: ["recommended"] });
    },
  });
  return (
    <form
      className="panel profile-form"
      onSubmit={(event) => {
        event.preventDefault();
        const values = new FormData(event.currentTarget);
        const result = { ...profile };
        for (const key of ["name", "email", "phone", "location"] as const)
          result[key] = String(values.get(key) ?? "").trim() || null;
        for (const key of [
          "summary",
          "education",
          "experience",
          "projects",
          "certifications",
        ] as const)
          result[key] = String(values.get(key) ?? "");
        result.skills = String(values.get("skills") ?? "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        const years = String(values.get("experience_years") ?? "");
        result.experience_years = years ? Number(years) : null;
        save.mutate(result);
      }}
    >
      <div className="form-grid">
        {(["name", "email", "phone", "location"] as const).map((key) => (
          <label key={key} className="capitalize">
            {key}
            <input
              name={key}
              type={key === "email" ? "email" : "text"}
              maxLength={key === "email" ? 320 : 250}
              defaultValue={profile[key] ?? ""}
            />
          </label>
        ))}
        <label>
          Years of experience
          <input
            type="number"
            name="experience_years"
            min="0"
            max="80"
            step="0.5"
            defaultValue={profile.experience_years ?? ""}
          />
        </label>
        <label>
          Skills (comma-separated)
          <input
            name="skills"
            defaultValue={profile.skills.join(", ")}
            placeholder="Python, SQL, Docker"
            maxLength={5000}
          />
        </label>
      </div>
      {(
        [
          "summary",
          "education",
          "experience",
          "projects",
          "certifications",
        ] as const
      ).map((key) => (
        <label className="capitalize" key={key}>
          {key}
          <textarea
            name={key}
            rows={key === "summary" ? 3 : 2}
            maxLength={10000}
            defaultValue={profile[key]}
          />
        </label>
      ))}
      <div className="form-actions">
        <button className="button" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save profile"}
        </button>
        {save.isSuccess && (
          <span role="status" className="success">
            <CheckCircle2 size={16} />
            Profile saved
          </span>
        )}
      </div>
      <Notice error={save.error} />
    </form>
  );
}
export function ProfilePage() {
  const result = useQuery({
    queryKey: ["profile"],
    queryFn: () => api<Profile>("/api/profile"),
  });
  const cache = useQueryClient();
  const remove = useMutation({
    mutationFn: () => api("/api/profile", { method: "DELETE" }),
    onSuccess: () => {
      void cache.invalidateQueries();
    },
  });
  return (
    <>
      <PageTitle
        eyebrow="YOUR STORY, IN YOUR WORDS"
        title="Your candidate profile"
        description="Review extracted information and add what matters. Unknown details stay blank."
        action={
          <Link className="button secondary" to="/resume">
            Upload resume <Upload size={16} />
          </Link>
        }
      />
      <Notice pending={result.isPending} error={result.error} />
      {result.data && (
        <ProfileForm
          key={JSON.stringify(result.data)}
          profile={{ ...emptyProfile, ...result.data }}
        />
      )}
      <div className="privacy-note">
        <h3>Your information stays in your workspace.</h3>
        <p>
          Placement analytics uses aggregate counts. Raw resume text is never
          shown in the TPO dashboard.
        </p>
        <button
          className="text-link danger"
          onClick={() => {
            if (
              window.confirm(
                "Delete your stored resumes, profile, saved jobs and application history?",
              )
            )
              remove.mutate();
          }}
          disabled={remove.isPending}
        >
          Delete my candidate data
        </button>
        <Notice error={remove.error} />
      </div>
    </>
  );
}
interface ResumeResult {
  id: string;
  filename: string;
  extracted_profile: Profile;
}
export function ResumePage() {
  const cache = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const upload = useMutation({
    mutationFn: () => {
      const data = new FormData();
      if (file) data.append("file", file);
      return api<ResumeResult>("/api/resumes", { method: "POST", body: data });
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["profile"] });
      void cache.invalidateQueries({ queryKey: ["recommended"] });
    },
  });
  return (
    <>
      <PageTitle
        eyebrow="START WITH WHAT YOU KNOW"
        title="Turn experience into opportunity."
        description="Upload a text-based PDF. Review the extracted details before using recommendations."
      />
      <div className="detail-grid">
        <section className="panel">
          <form
            className="upload-zone"
            onSubmit={(e) => {
              e.preventDefault();
              upload.mutate();
            }}
          >
            <div className="upload-icon">
              <Upload size={32} />
            </div>
            <h2>A small upload. A clearer search.</h2>
            <p className="muted">
              PDF only · up to 5 MB · no scanned or encrypted files
            </p>
            <label className="file-label">
              Choose your resume
              <input
                type="file"
                accept="application/pdf,.pdf"
                required
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  upload.reset();
                }}
              />
            </label>
            {file && <p>{file.name}</p>}
            <button className="button" disabled={!file || upload.isPending}>
              {upload.isPending ? "Reading your resume…" : "Extract profile"}
              <ArrowRight size={17} />
            </button>
          </form>
          <Notice error={upload.error} />
          {upload.data && (
            <div className="extraction-result">
              <h3>
                <CheckCircle2 size={20} /> Your resume is ready to review
              </h3>
              <div className="chips">
                {upload.data.extracted_profile.skills.map((skill) => (
                  <span key={skill} className="chip green">
                    {skill}
                  </span>
                ))}
              </div>
              <p>
                {upload.data.extracted_profile.email ??
                  "No email clearly identified."}
              </p>
              <Link className="button secondary" to="/profile">
                Review extracted profile <ArrowRight size={16} />
              </Link>
            </div>
          )}
        </section>
        <aside className="panel tips-panel">
          <Sparkles size={24} />
          <h2>Keep the story yours.</h2>
          <p>
            We identify known skills and clearly labeled sections. You can edit
            every extracted field.
          </p>
          <ul>
            <li>Use a PDF with selectable text.</li>
            <li>We leave uncertain information blank.</li>
            <li>No resume is sent to an employer.</li>
            <li>Delete your data from the profile page.</li>
          </ul>
        </aside>
      </div>
    </>
  );
}
export function RecommendedPage() {
  const [minScore, setMinScore] = useState("0");
  const [algorithm, setAlgorithm] = useState("production");
  const result = useQuery({
    queryKey: ["recommended", minScore, algorithm],
    queryFn: () =>
      api<Match[]>(
        `/api/jobs/recommended?min_score=${minScore}${algorithm === "production" ? "" : `&algorithm=${algorithm}`}`,
      ),
  });
  return (
    <>
      <PageTitle
        eyebrow="A MATCH YOU CAN UNDERSTAND"
        title="Opportunities, with a reason."
        description="Compare your skills with the opening. Every score comes with its working."
        action={
          <Link className="button secondary" to="/profile">
            Edit your profile <ArrowRight size={16} />
          </Link>
        }
      />
      <div className="filter-panel compact">
        <label>
          Minimum match
          <select
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
          >
            <option value="0">All matches</option>
            <option value="0.3">30% and above</option>
            <option value="0.5">50% and above</option>
            <option value="0.7">70% and above</option>
          </select>
        </label>
        <label>
          Ranking approach
          <select
            value={algorithm}
            onChange={(e) => setAlgorithm(e.target.value)}
          >
            <option value="production">Production model</option>
              <option value="hybrid">Hybrid, explained</option>
            <option value="tfidf">TF-IDF baseline</option>
            <option value="sentence_transformer">SentenceTransformer</option>
          </select>
        </label>
      </div>
      <Notice
        pending={result.isPending}
        error={result.error}
        empty={result.data?.length === 0}
      >
        Add your skills or resume, or lower the minimum match score.
      </Notice>
      <div className="recommendation-grid">
        {result.data?.map((match) => (
          <section key={match.job.id} className="recommendation">
            <JobCard job={match.job} match={match} />
            <div className="explanation">
              <span className="eyebrow">WHY THIS MATCH</span>
              <div className="breakdown">
                {(
                  [
                    "semantic",
                    "skill",
                    "eligibility",
                    "location",
                    "freshness",
                  ] as const
                ).map((key) => (
                  <div key={key}>
                    <span className="capitalize">{key}</span>
                    <strong>{percent(match[`${key}_score`])}</strong>
                  </div>
                ))}
              </div>
              <p>
                <strong>Matching:</strong>{" "}
                {match.matched_skills.join(", ") ||
                  "No explicit overlap identified"}
              </p>
              <p>
                <strong>To develop:</strong>{" "}
                {match.missing_skills.join(", ") ||
                  "No additional known skills identified"}
              </p>
              <ul>
                {match.explanation.slice(1).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <small>
                Model: {match.algorithm} · {match.model_version}
              </small>
              {match.fallback_reason && (
                <p className="fallback-note">{match.fallback_reason}</p>
              )}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
