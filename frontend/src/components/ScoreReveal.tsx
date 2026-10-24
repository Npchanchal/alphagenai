import { useI18n } from "../i18n";
import { formatCompanyScore, scoreClass } from "../lib/score";

type Props = {
  score: number | null | undefined;
  coverageStatus?: string | null;
  coverageReason?: string | null;
  testId?: string;
  size?: "lg" | "md";
};

/** Animated GCI level reveal — presence, not noise. */
export default function ScoreReveal({ score, coverageStatus, coverageReason, testId, size = "lg" }: Props) {
  const { t } = useI18n();
  const text = formatCompanyScore(score, 1, coverageStatus, coverageReason);
  const statusKey =
    score == null && coverageStatus ? `coverage.status.${coverageStatus}` : "";
  const label =
    score == null
      ? coverageReason
        ? coverageReason
        : coverageStatus
        ? t(statusKey)
        : t("ui.ScoreReveal.notScored")
      : text;
  return (
    <span
      className={`score-reveal score ${scoreClass(score)} size-${size}${score == null ? " score-reason" : ""}`}
      data-testid={testId}
    >
      {label === statusKey ? text : label}
    </span>
  );
}
