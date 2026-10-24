import { describe, expect, it } from "vitest";
import { isIndexingCrawler } from "./indexingCrawler";

describe("indexing crawlers", () => {
  it("lets search indexers through and keeps a normal browser out", () => {
    expect(
      isIndexingCrawler(
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
      ),
    ).toBe(true);
    expect(
      isIndexingCrawler(
        "Mozilla/5.0 (compatible; Google-InspectionTool/1.0)",
      ),
    ).toBe(true);
    expect(isIndexingCrawler("Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)")).toBe(
      true,
    );
    expect(isIndexingCrawler("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")).toBe(
      false,
    );
    expect(isIndexingCrawler("")).toBe(false);
  });
});
