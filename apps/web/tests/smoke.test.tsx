import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
describe("frontend", () => {
  it("renders accessible content", () => {
    render(<h1>CareerFlowOps</h1>);
    expect(screen.getByRole("heading")).toHaveTextContent("CareerFlowOps");
  });
});
