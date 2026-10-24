/**
 * Browsers that fetch a page in order to index it.
 * The seat wall is for visitors. These agents render the page.
 * Writes and paid reads stay behind the API.
 */

const INDEXING_CRAWLER =
  /googlebot|google-inspectiontool|googleother|google-extended|storebot-google|adsbot-google|mediapartners-google|apis-google|google-notebooklm|bingbot|bingpreview|msnbot|duckduckbot|baiduspider|yandex|applebot|slurp|petalbot|amazonbot|facebookexternalhit|twitterbot|linkedinbot|ia_archiver|oai-searchbot|chatgpt-user|gptbot|claudebot|claude-searchbot|claude-user|anthropic-ai|perplexitybot|perplexity-user|ccbot|bytespider|cohere-ai|diffbot|omgili|youbot/i;

export function isIndexingCrawler(userAgent?: string): boolean {
  const ua = userAgent ?? (typeof navigator === "undefined" ? "" : navigator.userAgent);
  return INDEXING_CRAWLER.test(ua);
}
