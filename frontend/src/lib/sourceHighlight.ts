/** Build a URL that asks the browser to highlight/search the cited quote. */

function pdfSearchPhrase(quote: string): string {
  const cleaned = quote
    .replace(/[^\p{L}\p{N}\s%.-]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
  const phrase = (cleaned || quote).split(" ").slice(0, 8).join(" ").slice(0, 80).trim();
  return phrase || quote.slice(0, 80);
}

export function withTextHighlight(url: string | null | undefined, quote?: string | null): string {
  const href = (url || "").trim();
  if (!href) return "";
  const q = (quote || "").trim().replace(/\s+/g, " ");
  const hashAt = href.indexOf("#");
  const base = hashAt >= 0 ? href.slice(0, hashAt) : href;
  if (!q) return href;
  const path = base.split("?")[0].toLowerCase();
  const isPdf = path.endsWith(".pdf") || path.includes(".pdf") || path.includes("/pdf");
  if (isPdf) {
    return `${base}#search=${encodeURIComponent(pdfSearchPhrase(q))}`;
  }
  const encodeFrag = (s: string) => encodeURIComponent(s).replace(/-/g, "%2D");
  if (q.length > 90) {
    return `${base}#:~:text=${encodeFrag(q.slice(0, 40))},${encodeFrag(q.slice(-40))}`;
  }
  return `${base}#:~:text=${encodeFrag(q.slice(0, 80))}`;
}

export type HighlightRange = { start: number; end: number };

const FOLD_CHARS: Record<string, string> = {
  "\u2018": "'",
  "\u2019": "'",
  "\u201A": "'",
  "\u201B": "'",
  "\u201C": '"',
  "\u201D": '"',
  "\u201E": '"',
  "\u201F": '"',
  "\u2010": "-",
  "\u2011": "-",
  "\u2012": "-",
  "\u2013": "-",
  "\u2014": "-",
  "\u2015": "-",
  "\u2212": "-",
  "\u00A0": " ",
};

/** Lower-case, straight quotes, collapsed whitespace, with original indexes. */
export function foldMap(text: string): { folded: string; index: number[] } {
  const chars: string[] = [];
  const index: number[] = [];
  let prevSpace = false;
  let i = 0;
  for (const raw of text) {
    let ch = raw.normalize("NFKC");
    ch = FOLD_CHARS[ch] ?? ch;
    if (/\s/u.test(ch)) {
      if (!prevSpace && chars.length > 0) {
        chars.push(" ");
        index.push(i);
        prevSpace = true;
      }
    } else {
      prevSpace = false;
      for (const c of ch.toLowerCase()) {
        chars.push(c);
        index.push(i);
      }
    }
    i += raw.length;
  }
  while (chars.length > 0 && chars[chars.length - 1] === " ") {
    chars.pop();
    index.pop();
  }
  return { folded: chars.join(""), index };
}

function rangeFromFold(index: number[], at: number, length: number): HighlightRange | null {
  if (at < 0 || length <= 0 || at + length > index.length) return null;
  const start = index[at];
  const end = index[at + length - 1] + 1;
  if (end <= start) return null;
  return { start, end };
}

function unwrapQuote(quote: string): string {
  return quote.replace(/^[\s"'“”‘’]+|[\s"'“”‘’]+$/g, "").trim();
}

function spanHoldsQuote(text: string, start: number, end: number, quote: string): boolean {
  if (start < 0 || end > text.length || end <= start) return false;
  const snippet = text.slice(start, end);
  const q = unwrapQuote(quote);
  if (!q) return true;
  if (snippet.includes(q) || q.includes(snippet)) return true;
  const left = foldMap(snippet).folded;
  const right = foldMap(q).folded;
  if (!left || !right) return false;
  return left.includes(right) || right.includes(left);
}

function searchFolded(text: string, quote: string): HighlightRange | null {
  const { folded, index } = foldMap(text);
  const needle = foldMap(unwrapQuote(quote)).folded;
  if (!folded || !needle) return null;
  const exact = folded.indexOf(needle);
  const hit = rangeFromFold(index, exact, needle.length);
  if (hit) return hit;
  const parts = needle
    .split(/\s*(?:\.{3}|…)\s*/)
    .map((part) => part.trim())
    .filter((part) => part.length >= 8);
  if (parts.length >= 2) {
    const a = folded.indexOf(parts[0]);
    const b = a >= 0 ? folded.indexOf(parts[parts.length - 1], a + parts[0].length) : -1;
    if (a >= 0 && b >= 0 && b - a < 800) {
      const end = b + parts[parts.length - 1].length;
      const span = rangeFromFold(index, a, end - a);
      if (span) return span;
    }
  }
  const words = needle.split(" ").filter((word) => word.length >= 4).slice(0, 8);
  if (words.length >= 3) {
    let from = 0;
    let startAt = -1;
    let endAt = -1;
    let matched = 0;
    for (const word of words) {
      const at = folded.indexOf(word, from);
      if (at < 0 || (startAt >= 0 && at - endAt > 240)) break;
      if (startAt < 0) startAt = at;
      endAt = at + word.length;
      from = endAt;
      matched += 1;
    }
    if (matched >= 3 && startAt >= 0 && endAt > startAt) {
      const span = rangeFromFold(index, startAt, endAt - startAt);
      if (span) return span;
    }
  }
  const short = needle.slice(0, 40);
  if (short.length >= 8) return rangeFromFold(index, folded.indexOf(short), short.length);
  return null;
}

/**
 * Char offsets of `quote` in `text`. A stored span is used only when it
 * actually contains the quote; otherwise the quote is located through
 * whitespace, quote, and dash differences.
 */
export function findQuoteRange(
  text: string,
  quote?: string | null,
  spanStart?: number | null,
  spanEnd?: number | null,
): HighlightRange | null {
  if (!text) return null;
  const q = (quote || "").trim();
  const spanOk =
    spanStart != null &&
    spanEnd != null &&
    spanStart >= 0 &&
    spanEnd > spanStart &&
    spanEnd <= text.length;
  if (spanOk && q && spanHoldsQuote(text, spanStart, spanEnd, q)) {
    const foldedSlice = foldMap(text.slice(spanStart, spanEnd)).folded;
    const foldedQuote = foldMap(unwrapQuote(q)).folded;
    if (foldedQuote && (foldedSlice === foldedQuote || foldedSlice.includes(foldedQuote))) {
      return { start: spanStart, end: spanEnd };
    }
  } else if (spanOk && !q) {
    return { start: spanStart, end: spanEnd };
  }
  if (!q) return null;
  const found = searchFolded(text, q);
  if (found) return found;
  if (spanOk && spanHoldsQuote(text, spanStart, spanEnd, q)) {
    return { start: spanStart, end: spanEnd };
  }
  return null;
}

export function splitHighlighted(
  text: string,
  range: HighlightRange | null,
): { before: string; match: string; after: string } | null {
  if (!range) return null;
  return {
    before: text.slice(0, range.start),
    match: text.slice(range.start, range.end),
    after: text.slice(range.end),
  };
}
