export function date(value: string | null): string {
  return value
    ? new Date(value).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Date not provided";
}
export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
