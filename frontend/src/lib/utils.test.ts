import { describe, it, expect } from "vitest";
import { formatCurrency, formatDate, truncate } from "./utils";

describe("Utility functions", () => {
  it("formats currency correctly", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
    expect(formatCurrency("invalid")).toBe("—");
    expect(formatCurrency(1500, "ZAR")).toContain("1");
    expect(formatCurrency("15420.50", "ZAR")).toContain("15");
  });

  it("formats date strings safely", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("")).toBe("—");
    expect(formatDate("2024-08-15")).toContain("2024");
  });

  it("truncates long strings", () => {
    expect(truncate("Short", 10)).toBe("Short");
    expect(truncate("This is a very long string", 10)).toBe("This is...");
  });
});
