import type { GuidanceProfile } from "../lib/api";

type Props = { profile?: GuidanceProfile | null };

export default function GuidanceProfileNote({ profile }: Props) {
  if (!profile || profile.closed_figures === 0) return null;
  const parts = [profile.results_vs_range, profile.in_year_revisions].filter((p) => p.sentence);
  return (
    <div className="dossier-profile" data-testid="guidance-profile">
      <ul className="about-list">
        {parts.map((p) => (
          <li key={p.sentence}>
            {p.label_text ? <strong>{p.label_text}. </strong> : null}
            {p.sentence}
          </li>
        ))}
        {profile.divergences.map((d) => (
          <li key={`${d.period}-${d.kind}-${d.metrics.join("-")}`} data-testid="guidance-divergence">
            {d.sentence}{" "}
            {d.sources.map((url, i) => (
              <a key={url} href={url} target="_blank" rel="noopener noreferrer" className="inline-link">
                [{i + 1}]
              </a>
            ))}
          </li>
        ))}
      </ul>
      <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
        {profile.note}
      </p>
    </div>
  );
}
