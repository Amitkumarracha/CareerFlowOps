import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { SavedPage } from "../src/pages/Saved";
import { RecommendedPage, ResumePage } from "../src/pages/Candidate";
import { ApplicationsPage } from "../src/pages/Applications";
import { Layout } from "../src/components/Layout";
import { MlopsPage } from "../src/pages/Operations";
import { api } from "../src/api/client";
import type { Job } from "../src/types";
const job: Job = {
  id: "unit-test",
  title: "Python engineer",
  company: "Test only",
  location: "Remote",
  description: "Unit test",
  employment_type: null,
  experience_level: null,
  remote: true,
  posted_at: null,
  first_seen_at: "2026-01-01",
  last_seen_at: "2026-01-01",
  skills: ["python"],
  apply_url: "https://example.org/apply",
  sources: [],
};
function mount(
  children: ReactNode,
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } }),
) {
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  sessionStorage.clear();
});
it("filters saved opportunities and keeps links to official applications", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(
          new Response(
            JSON.stringify([{ id: "bookmark", job, created_at: "2026-01-01" }]),
          ),
        ),
      ),
  );
  mount(<SavedPage />);
  expect(await screen.findByRole("link", { name: job.title })).toBeVisible();
  expect(screen.getByRole("link", { name: "Apply" })).toHaveAttribute(
    "href",
    job.apply_url,
  );
  fireEvent.change(screen.getByLabelText("Search saved jobs"), {
    target: { value: "no-such-title" },
  });
  expect(
    await screen.findByText("No saved opportunities match your search."),
  ).toBeVisible();
});
it("reviews and deletes a stored extraction through protected endpoints", async () => {
  let removed = false;
  const fetchMock = vi
    .fn()
    .mockImplementation((url: string, init: RequestInit) => {
      if (init.method === "DELETE") {
        removed = true;
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      const data = url.endsWith("/api/resumes")
        ? removed
          ? []
          : [{ id: "resume", filename: "test.pdf", created_at: "2026-01-01" }]
        : { extracted_text: "Private unit-test extraction" };
      return Promise.resolve(new Response(JSON.stringify(data)));
    });
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mount(<ResumePage />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Review extracted text" }),
  );
  expect(await screen.findByText("Private unit-test extraction")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Delete extraction" }));
  expect(
    await screen.findByText(/No resume extractions stored yet/),
  ).toBeVisible();
  expect(
    fetchMock.mock.calls.some(([, init]) => init.method === "DELETE"),
  ).toBe(true);
});
it("blocks an invalid upload before submitting it", async () => {
  const fetchMock = vi
    .fn()
    .mockImplementation(() => Promise.resolve(new Response("[]")));
  vi.stubGlobal("fetch", fetchMock);
  mount(<ResumePage />);
  fireEvent.change(screen.getByLabelText("Choose your resume"), {
    target: {
      files: [new File(["text"], "resume.txt", { type: "text/plain" })],
    },
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Choose a nonempty PDF up to 5 MB",
  );
  expect(
    screen.getByRole("button", { name: /Extract profile/ }),
  ).toBeDisabled();
  expect(fetchMock.mock.calls.some(([, init]) => init.method === "POST")).toBe(
    false,
  );
});
it("filters applications by status without changing persisted records", async () => {
  const data = [
    {
      id: "a",
      job,
      status: "SAVED",
      notes: "",
      history: [],
      updated_at: "2026-01-01",
    },
    {
      id: "b",
      job: { ...job, id: "other", title: "Design researcher" },
      status: "INTERVIEW",
      notes: "",
      history: [],
      updated_at: "2026-01-01",
    },
  ];
  const fetchMock = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(data))),
    );
  vi.stubGlobal("fetch", fetchMock);
  mount(<ApplicationsPage />);
  await screen.findByRole("link", { name: "Design researcher" });
  fireEvent.change(
    screen.getByRole("combobox", { name: "Application status" }),
    { target: { value: "INTERVIEW" } },
  );
  expect(
    screen.queryByRole("link", { name: job.title }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Design researcher" })).toBeVisible();
  expect(fetchMock.mock.calls.every(([, init]) => !init.method)).toBe(true);
});
it("disconnect clears cached private results and the session tokens", async () => {
  sessionStorage.setItem("careerflowops-candidate", "unit-test-token");
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(new Response("{}", { status: 401 })),
      ),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(
    ["saved"],
    [{ id: "private", job, created_at: "2026-01-01" }],
  );
  mount(
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SavedPage />} />
      </Route>
    </Routes>,
    client,
  );
  expect(await screen.findByRole("link", { name: job.title })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Workspace access" }));
  fireEvent.click(screen.getByRole("button", { name: "Disconnect this tab" }));
  await waitFor(() => expect(sessionStorage.length).toBe(0));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "candidate access token",
  );
  expect(
    screen.queryByRole("link", { name: job.title }),
  ).not.toBeInTheDocument();
});
it("filters evaluation splits using only the saved artifact", async () => {
  const result = {
    registry: null,
    status_message: "Unit-test saved artifact",
    evaluation: {
      selected_algorithm: "tfidf",
      dataset_version: "test",
      labels_description: "Unit-test data only",
      results: [
        {
          algorithm: "tfidf",
          split: "validation",
          metrics: { ndcg_at_5: 0.123 },
        },
        { algorithm: "hybrid", split: "test", metrics: { ndcg_at_5: 0.456 } },
      ],
    },
  };
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(new Response(JSON.stringify(result))),
      ),
  );
  mount(<MlopsPage />);
  expect(await screen.findByText("0.123")).toBeVisible();
  fireEvent.change(screen.getByRole("combobox", { name: "Evaluation split" }), {
    target: { value: "test" },
  });
  expect(screen.queryByText("0.123")).not.toBeInTheDocument();
  expect(screen.getByText("0.456")).toBeVisible();
});
it("reports offline and structured validation errors in plain language", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
  );
  await expect(api("/api/profile")).rejects.toThrow("Cannot reach the API");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            detail: [
              {
                loc: ["body", "experience_years"],
                msg: "Must be nonnegative",
              },
            ],
          }),
          { status: 422 },
        ),
      ),
    ),
  );
  await expect(api("/api/profile")).rejects.toThrow(
    "experience_years: Must be nonnegative",
  );
});

it("locks production recommendations to the verified release algorithm", async () => {
  const fetchMock = vi.fn().mockImplementation((url: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          url.endsWith("/ready")
            ? {
                status: "ready",
                bundle_id: "unit-test-bundle",
                model_version: "test",
                algorithm: "tfidf",
              }
            : [],
        ),
      ),
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  mount(<RecommendedPage />);
  await waitFor(() =>
    expect(
      screen.getByRole("combobox", { name: "Ranking approach" }),
    ).toBeDisabled(),
  );
  expect(
    screen.getByText(/Serving verified production release: tfidf/),
  ).toBeVisible();
  expect(
    fetchMock.mock.calls
      .filter(([url]) => url.includes("recommended"))
      .every(([url]) => !url.includes("algorithm=")),
  ).toBe(true);
});
