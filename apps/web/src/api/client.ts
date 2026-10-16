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
  let response: Response;
  try {
    response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}${path}`,
      { ...init, headers },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new Error(
      "Cannot reach the API. Check the service connection and try again.",
    );
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403)
      throw new Error(
        `Connect your ${role} access token using Workspace access above.`,
      );
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body ? body.detail : null;
    const validation = Array.isArray(detail)
      ? detail
          .map(
            (item: { loc?: unknown[]; msg?: string }) =>
              `${item.loc?.slice(1).join(".") || "Input"}: ${item.msg ?? "Invalid value"}`,
          )
          .join("; ")
      : null;
    throw new Error(
      typeof detail === "string"
        ? detail
        : validation ||
            `Request failed (${response.status}). Check your input and try again.`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
