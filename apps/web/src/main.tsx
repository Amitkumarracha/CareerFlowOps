import React from "react";
import ReactDOM from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import "./style.css";
export function HealthPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const r = await fetch(
        `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/health`,
      );
      if (!r.ok) throw new Error("API unavailable");
      return r.json() as Promise<{ status: string }>;
    },
  });
  return (
    <main>
      <h1>CareerFlowOps</h1>
      <p>Discover earlier. Match smarter. Apply better.</p>
      <p role="status">
        {health.isPending
          ? "Checking API…"
          : health.error
            ? "API unavailable"
            : `API: ${health.data.status}`}
      </p>
    </main>
  );
}
const client = new QueryClient();
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <HealthPage />
    </QueryClientProvider>
  </React.StrictMode>,
);
