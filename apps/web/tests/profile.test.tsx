import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ProfilePage } from "../src/pages/Candidate";
import type { Profile } from "../src/types";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("submits the candidate-edited profile with typed experience and skills", async () => {
  const profile: Profile = {
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
  const fetchMock = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(profile))),
    );
  vi.stubGlobal("fetch", fetchMock);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const skills = await screen.findByLabelText("Skills (comma-separated)");
  fireEvent.change(skills, { target: { value: "Python, SQL" } });
  fireEvent.change(screen.getByLabelText("Years of experience"), {
    target: { value: "3.5" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(
        (call: unknown[]) => (call[1] as RequestInit)?.method === "PUT",
      ),
    ).toBe(true),
  );
  const call = fetchMock.mock.calls.find(
    (call: unknown[]) => (call[1] as RequestInit)?.method === "PUT",
  );
  const body = JSON.parse(String((call?.[1] as RequestInit).body)) as Profile;
  expect(body.skills).toEqual(["Python", "SQL"]);
  expect(body.experience_years).toBe(3.5);
  expect(body.name).toBeNull();
});
