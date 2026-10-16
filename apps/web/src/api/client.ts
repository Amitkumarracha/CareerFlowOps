export function token(role: "candidate" | "admin"): string {
  return sessionStorage.getItem(`careerflowops-${role}`) ?? "";
}
export async function api<T>(
  path: string,
  init: RequestInit = {},
  role: "candidate" | "admin" = "candidate",
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body)
    headers.set("Content-Type", "application/json");
  if (token(role)) headers.set("Authorization", `Bearer ${token(role)}`);
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}${path}`,
    { ...init, headers },
  );
  if (!response.ok) {
    if (response.status === 401 || response.status === 403)
      throw new Error(
        `Connect your ${role} access token using Workspace access above.`,
      );
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body ? body.detail : null;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status}). Check your input and try again.`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
