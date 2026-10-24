# CiteAlpha Holdings

Holdings-weighted view of published company records for a mutual-fund, PMS, AIF, or pension file.

## What the desk uploads

A dated file: ISIN, weight, and an optional residual kind (`cash`, `debt`, `indirect`, `other`).

## What comes back

- Weighted published GCI of the names that have a score
- Share of the file those names represent
- Names with no score, listed and left out of the figure
- Cash, debt, indirect, and unresolved ISINs in their own bucket
- A diff against the previous file saved for that desk

## Access

An admin approves a pilot and sets the term to 30, 45, or 60 days. Holdings is open for that term. After the term it stays on a paid Desk, Enterprise, or One-Stop seat.

The page reads the published score cache and the Commitment Record. It does not recompute a score.
