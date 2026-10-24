import { useI18n } from "../i18n";
import type { OutcomeView } from "../lib/api";
import { buildRecordParts } from "../lib/score";

type Props = {
  outcomes: OutcomeView[];
  coverageReason?: string | null;
  testId?: string;
};

/** One-sentence delivery record for the dossier header (plan W3.1). */
export default function RecordSentence({ outcomes, coverageReason, testId = "dossier-record" }: Props) {
  const { t } = useI18n();
  const parts = buildRecordParts(outcomes);
  if (parts.closed === 0) {
    return (
      <p className="dossier-record" data-testid={testId}>
        {coverageReason || t("dossier.record.empty")}
      </p>
    );
  }
  return (
    <p className="dossier-record" data-testid={testId}>
      {t("dossier.record.metric", {
        metric: parts.metricLabel,
        metOrBeat: parts.metOrBeat,
        closed: parts.closed,
        missedClause: parts.missedClause,
      })}
    </p>
  );
}
