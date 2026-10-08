import { describe, expect, it } from "vitest";
import { safeNextPath } from "./navigation";

describe("safeNextPath", () => {
  it.each(["/\\evil.test", "/%5cevil.test", "/%255cevil.test", "//evil.test", "/%2fevil.test", "/\tevil.test", "/%0aevil.test", "/%250devil.test", "/auth/login", "/%61uth/login", "https://evil.test", "/bad%ZZ"])("rejects %s", (value) => {
    expect(safeNextPath(value)).toBe("/dashboard");
  });
  it("keeps a relative course path and query", () => {
    expect(safeNextPath("/courses/one?tab=lessons")).toBe("/courses/one?tab=lessons");
  });
});
