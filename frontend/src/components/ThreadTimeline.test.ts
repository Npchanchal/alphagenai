import { describe, expect, it } from "vitest";
import { chartPointerX, nearestChartIndex } from "./ThreadTimeline";

function yearXs(count: number, right = 36): number[] {
  const width = 640;
  const left = 12;
  const inner = width - left - right;
  return Array.from({ length: count }, (_, i) => left + (i / (count - 1)) * inner);
}

describe("promise thread chart hover", () => {
  it("reads the latest year when a wide box letterboxes the drawing", () => {
    const xs = yearXs(5);
    const view = { width: 640, height: 168 };
    const rect = { left: 40, width: 1100, height: 168 };
    const offsetX = (rect.width - view.width) / 2;
    const latest = xs[xs.length - 1];
    const clientX = rect.left + offsetX + latest;
    expect(nearestChartIndex(chartPointerX(clientX, rect, view), xs)).toBe(xs.length - 1);
    const stretched = ((clientX - rect.left) / rect.width) * view.width;
    expect(nearestChartIndex(stretched, xs)).toBe(xs.length - 2);
  });

  it("keeps the first and last year on a narrow chart", () => {
    const xs = yearXs(5);
    const view = { width: 640, height: 168 };
    const rect = { left: 16, width: 320, height: 168 };
    const scale = rect.width / view.width;
    for (const x of [xs[0], xs[2], xs[xs.length - 1]]) {
      const clientX = rect.left + x * scale;
      expect(nearestChartIndex(chartPointerX(clientX, rect, view), xs)).toBe(xs.indexOf(x));
    }
  });
});
