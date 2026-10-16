import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { JobsPage } from "../src/pages/Jobs";
import { JobCard } from "../src/components/JobCard";
import { api } from "../src/api/client";
import type { Job } from "../src/types";
import type { ReactNode } from "react";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  sessionStorage.clear();
});
function wrapper(children: ReactNode) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}
const job: Job = {
  id: "fixture",
  title: "Test engineer",
  company: "Test fixture",
  location: "Test city",
  description: "Test only",
  employment_type: null,
  experience_level: null,
  remote: null,
  posted_at: null,
  first_seen_at: "2026-01-01",
  last_seen_at: "2026-01-01",
  skills: ["python"],
  apply_url: "https://boards.greenhouse.io/example/jobs/1",
  sources: [],
};

describe("job discovery", () => {
  it("shows an empty state and sends filters to the API", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({ items: [], total: 0, limit: 12, offset: 0 }),
          ),
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    render(wrapper(<JobsPage />));
    expect(await screen.findByText("Nothing here yet")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Search jobs"), {
      target: { value: "Python" },
    });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("keyword=Python"),
        expect.any(Object),
      ),
    );
  });
  it("shows failed requests without fake job cards", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Source unavailable" }), {
          status: 503,
        }),
      ),
    );
    render(wrapper(<JobsPage />));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Source unavailable",
    );
  });
  it("uses the official URL and saves through the authenticated API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    sessionStorage.setItem("careerflowops-candidate", "test-token");
    render(wrapper(<JobCard job={job} />));
    expect(screen.getByRole("link", { name: /Apply/ })).toHaveAttribute(
      "href",
      job.apply_url,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save Test engineer" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Saved");
    const options = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(new Headers(options.headers).get("Authorization")).toBe(
      "Bearer test-token",
    );
  });
  it("explains missing access for private pages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 401 })),
    );
    await expect(api("/api/profile")).rejects.toThrow("candidate access token");
  });
});
