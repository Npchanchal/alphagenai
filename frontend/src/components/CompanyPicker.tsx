import type { CompanySummary } from "../lib/api";

type Props = {
  companies: CompanySummary[];
  value: string;
  onChange: (id: string) => void;
  label?: string;
  testId?: string;
  allLabel?: string;
};

export default function CompanyPicker({
  companies,
  value,
  onChange,
  label = "Company",
  testId,
  allLabel,
}: Props) {
  return (
    <label className="company-picker">
      <span className="field-label">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testId}
      >
        {allLabel && <option value="">{allLabel}</option>}
        {companies.map((c) => (
          <option key={c.id} value={c.id}>
            {c.ticker} — {c.name}
          </option>
        ))}
      </select>
    </label>
  );
}
