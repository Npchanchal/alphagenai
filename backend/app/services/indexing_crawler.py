"""User agents that fetch a page in order to index it.

The guest dossier cap is for visitors. An indexer still has to receive the
public dossier. Seat-gated writes are unchanged.
"""

from __future__ import annotations

import re

_INDEXING = re.compile(
    r"googlebot|google-inspectiontool|googleother|google-extended|storebot-google|"
    r"adsbot-google|mediapartners-google|apis-google|google-notebooklm|"
    r"bingbot|bingpreview|msnbot|duckduckbot|baiduspider|yandex|applebot|slurp|"
    r"petalbot|amazonbot|facebookexternalhit|twitterbot|linkedinbot|ia_archiver|"
    r"oai-searchbot|chatgpt-user|gptbot|claudebot|claude-searchbot|claude-user|"
    r"anthropic-ai|perplexitybot|perplexity-user|ccbot|bytespider|cohere-ai|"
    r"diffbot|omgili|youbot",
    re.IGNORECASE,
)


def is_indexing_crawler(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    return _INDEXING.search(user_agent) is not None
