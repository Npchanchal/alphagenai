import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { trackEvent } from "../lib/analytics";
import { fetchAbuseChallenge, postPilotRequest } from "../lib/api";
import { useI18n } from "../i18n";

type Props = {
  source?: string;
  compact?: boolean;
};

export default function PilotRequestForm({ source = "landing", compact = false }: Props) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [firm, setFirm] = useState("");
  const [role, setRole] = useState("");
  const [teamSize, setTeamSize] = useState("");
  const [message, setMessage] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [challengePrompt, setChallengePrompt] = useState("");
  const [challengeAnswer, setChallengeAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadChallenge() {
    try {
      const ch = await fetchAbuseChallenge();
      setChallengeId(ch.challenge_id);
      setChallengePrompt(ch.prompt);
      setChallengeAnswer("");
    } catch {
      setChallengePrompt(t("ui.PilotRequestForm.challengeError"));
    }
  }

  useEffect(() => {
    void loadChallenge();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await postPilotRequest({
        name,
        email,
        firm,
        role: role || undefined,
        team_size: teamSize || undefined,
        message: message || undefined,
        challenge_id: challengeId,
        challenge_answer: challengeAnswer,
      });
      trackEvent("pilot_cta", { source, type: "form" });
      setSubmittedEmail(email);
      setSuccess(true);
      setName("");
      setEmail("");
      setFirm("");
      setRole("");
      setTeamSize("");
      setMessage("");
      setChallengeAnswer("");
      void loadChallenge();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("ui.PilotRequestForm.submitError"));
      void loadChallenge();
    } finally {
      setBusy(false);
    }
  }

  if (success) {
    return (
      <div className="pilot-form-success" data-testid="pilot-request-success">
        <p>
          <strong>{t("ui.PilotRequestForm.received")}</strong> {t("ui.PilotRequestForm.followUp")}{" "}
          <strong>{submittedEmail}</strong>.
        </p>
        <p className="muted">
          {t("ui.PilotRequestForm.alsoReview")}{" "}
          <Link to="/products#plans">{t("ui.PilotRequestForm.packages")}</Link> {t("ui.PilotRequestForm.orOpen")}{" "}
          <Link to="/trust">{t("footer.trust")}</Link> {t("ui.PilotRequestForm.whileWait")}
        </p>
        <button type="button" className="btn" onClick={() => setSuccess(false)}>
          {t("ui.PilotRequestForm.another")}
        </button>
      </div>
    );
  }

  return (
    <form
      className={`auth-form pilot-request-form${compact ? " pilot-request-form--compact" : ""}`}
      onSubmit={(e) => void onSubmit(e)}
      data-testid="pilot-request-form"
    >
      <div className="pilot-form-grid">
        <label>
          {t("ui.PilotRequestForm.fullName")}
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            data-testid="pilot-name"
          />
        </label>
        <label>
          {t("ui.PilotRequestForm.workEmail")}
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            data-testid="pilot-email"
          />
        </label>
        <label>
          {t("ui.PilotRequestForm.firm")}
          <input
            type="text"
            required
            value={firm}
            onChange={(e) => setFirm(e.target.value)}
            autoComplete="organization"
            data-testid="pilot-firm"
          />
        </label>
        <label>
          {t("ui.PilotRequestForm.role")}
          <input
            type="text"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            autoComplete="organization-title"
            placeholder={t("ui.PilotRequestForm.rolePlaceholder")}
            data-testid="pilot-role"
          />
        </label>
        <label>
          {t("ui.PilotRequestForm.teamSize")}
          <select value={teamSize} onChange={(e) => setTeamSize(e.target.value)} data-testid="pilot-team-size">
            <option value="">{t("ui.PilotRequestForm.select")}</option>
            <option value="1–5">{t("ui.PilotRequestForm.analysts", { n: "1–5" })}</option>
            <option value="6–15">{t("ui.PilotRequestForm.analysts", { n: "6–15" })}</option>
            <option value="16–40">{t("ui.PilotRequestForm.analysts", { n: "16–40" })}</option>
            <option value="40+">{t("ui.PilotRequestForm.analysts", { n: "40+" })}</option>
          </select>
        </label>
      </div>
      <label>
        {t("ui.PilotRequestForm.notes")}
        <textarea
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t("ui.PilotRequestForm.notesPlaceholder")}
          data-testid="pilot-message"
        />
      </label>
      {challengePrompt ? (
        <label>
          {t("ui.PilotRequestForm.verification", { prompt: challengePrompt })}
          <input
            type="text"
            required
            inputMode="numeric"
            value={challengeAnswer}
            onChange={(e) => setChallengeAnswer(e.target.value)}
            data-testid="pilot-challenge"
          />
        </label>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      <button type="submit" className="btn primary" disabled={busy || !challengeId} data-testid="pilot-submit">
        {busy ? t("ui.PilotRequestForm.sending") : t("footer.pilot")}
      </button>
      <p className="muted pilot-form-note">
        {t("ui.PilotRequestForm.note")}
      </p>
    </form>
  );
}
