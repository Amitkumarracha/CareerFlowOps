export interface Occurrence {
  source_name: string;
  source_job_id: string;
  source_url: string;
  apply_url: string;
  verification_status: string;
  verified_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
}
export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  employment_type: string | null;
  experience_level: string | null;
  remote: boolean | null;
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  skills: string[];
  apply_url: string | null;
  sources: Occurrence[];
}
export interface JobList {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}
export interface Profile {
  name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  experience_years: number | null;
  skills: string[];
  summary: string;
  education: string;
  experience: string;
  projects: string;
  certifications: string;
}
export interface Match {
  job: Job;
  overall_score: number;
  semantic_score: number;
  skill_score: number;
  eligibility_score: number;
  location_score: number;
  freshness_score: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string[];
  algorithm: string;
  model_version: string;
  fallback_reason: string | null;
}
export type Status =
  "SAVED" | "APPLIED" | "INTERVIEW" | "OFFER" | "REJECTED" | "WITHDRAWN";
export interface Application {
  id: string;
  job: Job;
  status: Status;
  notes: string;
  updated_at: string;
  history: { status: Status; notes: string; changed_at: string }[];
}
export interface IngestionRun {
  id: string;
  mode: string;
  status: string;
  created_at: string;
  counts: { fetched?: number; normalized?: number; duplicates?: number };
  errors: string[];
}
