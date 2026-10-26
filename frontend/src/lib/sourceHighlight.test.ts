import { describe, expect, it } from "vitest";
import { findQuoteRange, withTextHighlight } from "./sourceHighlight";

describe("withTextHighlight", () => {
  it("adds a text fragment on HTML URLs", () => {
    const href = withTextHighlight("https://ir.example.com/call.html", "growth 5-7%");
    expect(href).toContain("#:~:text=");
    expect(href).toContain("growth");
  });

  it("uses PDF search fragments", () => {
    const href = withTextHighlight(
      "https://www.cipla.com/sites/default/files/Transcript-Q4FY23.pdf",
      "EBITDA margin was 24.5%",
    );
    expect(href).toContain("#search=");
    expect(href).toContain("EBITDA");
  });

  it("returns empty for missing URL", () => {
    expect(withTextHighlight("", "quote")).toBe("");
  });
});

describe("findQuoteRange", () => {
  it("prefers explicit spans", () => {
    expect(findQuoteRange("abcdef", "cd", 2, 4)).toEqual({ start: 2, end: 4 });
  });

  it("finds a case-insensitive quote", () => {
    const text = "We expect Margins to remain in a tight band.";
    const r = findQuoteRange(text, "margins to remain");
    expect(r).toEqual({ start: 10, end: 27 });
  });

  it("matches across line breaks, curly quotes, and dashes", () => {
    const text = "We expect “Margins” to\nremain — in a tight band.";
    const r = findQuoteRange(text, "Margins to remain - in a tight");
    expect(r).not.toBeNull();
    expect(text.slice(r!.start, r!.end).replace(/\s+/g, " ")).toContain("Margins");
    expect(text.slice(r!.start, r!.end)).toContain("tight");
  });

  it("ignores a span that does not contain the quote", () => {
    const text = "intro. The margin was 21.1 percent for the year.";
    const r = findQuoteRange(text, "margin was 21.1 percent", 0, 6);
    expect(text.slice(r!.start, r!.end)).toBe("margin was 21.1 percent");
  });

  it("joins an ellipsis in the stored quote", () => {
    const text = "Revenue grew 19.7 percent in constant currency for the full year.";
    const r = findQuoteRange(text, "Revenue grew … for the full year");
    expect(text.slice(r!.start, r!.end)).toContain("19.7");
    expect(text.slice(r!.start, r!.end)).toContain("full year");
  });
});
