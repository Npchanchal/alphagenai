import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CompanyPicker from "../components/CompanyPicker";
import PlanAccessGate from "../components/PlanAccessGate";
import {
  deleteAnalystMemory,
  deleteAnalystProject,
  downloadAnalystExport,
  type AnalystExportFormat,
  deleteAnalystUpload,
  fetchAnalystProjects,
  postAnalystMemory,
  postAnalystModel,
  postAnalystProject,
  postAnalystUpload,
  type AnalystProject,
  deleteAnalystMonitor,
  fetchAnalystFeed,
  fetchAnalystMonitors,
  fetchAnalystRun,
  fetchAnalystRuns,
  fetchAnalystSkills,
  fetchCompanies,
  fetchCompanyCommitments,
  postAnalystMonitor,
  postAnalystRun,
  type AnalystMonitor,
  type AnalystRun,
  type AnalystRunSummary,
  type AnalystSkill,
  type CommitmentView,
  type CompanySummary,
  type AnalystMonitorScope,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { groupAnalystSkills } from "../lib/seatLanding";
import { useI18n } from "../i18n";
import {
  DestinationsPanel,
  DigestPanel,
  HouseStylePanel,
  KeysPanel,
  errorText,
  toBase64,
} from "./analyst/AnalystSettings";

function download(name: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function Cites({ ns, runId }: { ns: number[]; runId: string }) {
  return (
    <>
      {ns.map((n) => (
        <a key={n} href={`#${runId}-src-${n}`} className="cite-marker">
          [{n}]
        </a>
      ))}
    </>
  );
}

const EXPORTS: [AnalystExportFormat, string][] = [
  ["xlsx", "analyst.export.xlsx"],
  ["pptx", "analyst.export.pptx"],
  ["pdf", "analyst.export.pdf"],
  ["md", "analyst.export.md"],
];

function RunOutput({ run }: { run: AnalystRun }) {
  const { t } = useI18n();
  const [exporting, setExporting] = useState<AnalystExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const shown = run.sections.filter((s) => s.claims.length > 0);
  return (
    <article className="panel analyst-output" data-testid="analyst-output">
      <div className="panel-head">
        <h2>
          {run.skill.title}: {run.company_name}
        </h2>
      </div>
      <p className="muted">
        {t("analyst.dataAsOf", { date: run.as_of })} · {run.disclaimer}
      </p>
      {run.project && (
        <p className="muted analyst-small">{t("analyst.projects.ranIn", { name: run.project.name })}</p>
      )}
      {run.trigger && (
        <p className="muted analyst-small">
          {t("analyst.monitors.triggeredBy", {
            title: run.trigger.title || "",
            date: run.trigger.date || "",
          })}
        </p>
      )}
      {run.headline && <p className="analyst-headline">{run.headline}</p>}
      {shown.map((s) => (
        <section key={s.id} className="analyst-section">
          <h3>{s.title}</h3>
          <ul>
            {s.claims.map((c, i) => (
              <li key={i}>
                {c.text} <Cites ns={c.cites} runId={run.run_id} />
              </li>
            ))}
          </ul>
        </section>
      ))}
      {run.not_found.length > 0 && (
        <section className="analyst-section">
          <h3>{t("analyst.notFound")}</h3>
          <ul className="muted">
            {run.not_found.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </section>
      )}
      <section className="analyst-section">
        <h3>{t("analyst.sources")}</h3>
        <ol className="analyst-sources">
          {run.citations.map((c) => (
            <li key={c.n} id={`${run.run_id}-src-${c.n}`}>
              {c.source_url && /^https?:\/\//.test(c.source_url) ? (
                <a href={c.source_url} target="_blank" rel="noreferrer">
                  {c.title || c.source_url}
                </a>
              ) : c.source_url?.startsWith("/") ? (
                <a href={c.source_url}>{c.title || c.source_url}</a>
              ) : (
                c.title
              )}{" "}
              <span className="muted">{c.date || ""}</span>
              {c.permalink && (
                <>
                  {" · "}
                  <a href={c.permalink} className="analyst-small">
                    {t("analyst.citationPage")}
                  </a>
                </>
              )}
              {c.quote && <blockquote>{c.quote}</blockquote>}
            </li>
          ))}
        </ol>
      </section>
      <p className="muted analyst-small">
        {t("analyst.checked", { kept: run.verifier.kept, removed: run.verifier.removed })}
      </p>
      <div className="analyst-actions">
        {EXPORTS.map(([fmt, key]) => (
          <button
            key={fmt}
            type="button"
            className="btn"
            disabled={exporting !== null}
            data-testid={`analyst-export-${fmt}`}
            onClick={() => {
              setExporting(fmt);
              setExportError(null);
              downloadAnalystExport(run.run_id, fmt)
                .catch((e) => setExportError(errorText(e, t("analyst.export.err"))))
                .finally(() => setExporting(null));
            }}
          >
            {exporting === fmt ? t("analyst.export.working") : t(key)}
          </button>
        ))}
        <button
          type="button"
          className="btn ghost"
          onClick={() =>
            download(
              `${run.run_id}-evidence-receipt.json`,
              JSON.stringify(run.evidence_receipt, null, 2),
              "application/json",
            )
          }
        >
          {t("analyst.downloadReceipt")}
        </button>
      </div>
      <p className="muted analyst-small">{t("analyst.export.note")}</p>
      {exportError && <p className="error">{exportError}</p>}
    </article>
  );
}

function CommitmentPanel({ view }: { view: CommitmentView }) {
  const { t } = useI18n();
  return (
    <section className="panel" data-testid="analyst-commitments">
      <div className="panel-head">
        <h2>{t("analyst.commitments.title")}</h2>
      </div>
      <p>{view.summary.sentence}</p>
      <p className="muted analyst-small">{view.note}</p>
      {view.commitments.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>{t("analyst.commitments.subject")}</th>
              <th>{t("analyst.commitments.type")}</th>
              <th>{t("analyst.commitments.due")}</th>
              <th>{t("analyst.commitments.status")}</th>
            </tr>
          </thead>
          <tbody>
            {view.commitments.map((c) => (
              <tr key={c.id}>
                <td>
                  <a href={c.source_url} target="_blank" rel="noreferrer" title={c.quote}>
                    {c.subject}
                  </a>
                </td>
                <td>{c.type_label}</td>
                <td>{c.due_period}</td>
                <td>{c.state_label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

function ProjectsPanel({
  projects,
  projectId,
  companyId,
  companyName,
  onSelect,
  onChanged,
}: {
  projects: AnalystProject[];
  projectId: string;
  companyId: string;
  companyName: string;
  onSelect: (id: string) => void;
  onChanged: (selectId?: string) => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [memory, setMemory] = useState("");
  const [modelName, setModelName] = useState("");
  const [modelFigure, setModelFigure] = useState("");
  const [modelUnit, setModelUnit] = useState("");
  const [modelAssumptions, setModelAssumptions] = useState("");
  const [modelSources, setModelSources] = useState("");
  const [modelMissing, setModelMissing] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const project = projects.find((p) => p.project_id === projectId) || null;

  async function act(fn: () => Promise<unknown>, after?: () => void) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      after?.();
    } catch (e) {
      setError(errorText(e, t("analyst.projects.err")));
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    if (!project) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      setError(t("analyst.projects.tooLarge"));
      return;
    }
    await act(
      async () =>
        postAnalystUpload(project.project_id, { filename: file.name, content_base64: await toBase64(file) }),
      () => onChanged(),
    );
  }

  return (
    <section className="panel" data-testid="analyst-projects">
      <div className="panel-head">
        <h2>{t("analyst.projects.title")}</h2>
      </div>
      <p className="muted analyst-small">{t("analyst.projects.lede")}</p>
      <div className="analyst-monitor-form">
        <label>
          {t("analyst.projects.current")}
          <select value={projectId} onChange={(e) => onSelect(e.target.value)} data-testid="analyst-project-select">
            <option value="">{t("analyst.projects.none")}</option>
            {projects.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("analyst.projects.newName")}
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("analyst.projects.namePlaceholder")} />
        </label>
        <button
          type="button"
          className="btn"
          disabled={busy || !name.trim() || !companyId}
          onClick={() =>
            void act(async () => {
              const p = await postAnalystProject({ name: name.trim(), company_ids: [companyId] });
              setName("");
              onChanged(p.project_id);
            })
          }
          data-testid="analyst-project-create"
        >
          {t("analyst.projects.create", { company: companyName })}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {project && (
        <div className="analyst-project-body">
          <p className="muted analyst-small">
            {t("analyst.projects.companies")}: {project.company_ids.join(", ") || "—"}
          </p>
          <h3>{t("analyst.projects.memory")}</h3>
          <p className="muted analyst-small">{t("analyst.projects.memoryLede")}</p>
          <ul className="doc-list">
            {project.memory.map((m) => (
              <li key={m.id}>
                {m.text}{" "}
                <button
                  type="button"
                  className="btn ghost small"
                  disabled={busy}
                  onClick={() => void act(() => deleteAnalystMemory(project.project_id, m.id), () => onChanged())}
                >
                  {t("analyst.monitors.remove")}
                </button>
              </li>
            ))}
          </ul>
          <div className="analyst-monitor-form">
            <input
              value={memory}
              maxLength={500}
              onChange={(e) => setMemory(e.target.value)}
              placeholder={t("analyst.projects.memoryPlaceholder")}
            />
            <button
              type="button"
              className="btn"
              disabled={busy || !memory.trim()}
              onClick={() =>
                void act(
                  () => postAnalystMemory(project.project_id, memory.trim()),
                  () => {
                    setMemory("");
                    onChanged();
                  },
                )
              }
            >
              {t("analyst.projects.remember")}
            </button>
          </div>
          <h3>{t("analyst.projects.models")}</h3>
          <p className="muted analyst-small">{t("analyst.projects.modelsLede")}</p>
          <ul className="doc-list" data-testid="analyst-models">
            {(project.models || []).map((model) => (
              <li key={model.model_id}>
                {model.name}: {model.figure} {model.unit} ({model.as_of}). {model.statement}
              </li>
            ))}
          </ul>
          <div className="analyst-monitor-form">
            <input value={modelName} onChange={(e) => setModelName(e.target.value)} placeholder={t("analyst.projects.modelName")} />
            <input value={modelFigure} onChange={(e) => setModelFigure(e.target.value)} placeholder={t("analyst.projects.modelFigure")} />
            <input value={modelUnit} onChange={(e) => setModelUnit(e.target.value)} placeholder={t("analyst.projects.modelUnit")} />
            <input value={modelAssumptions} onChange={(e) => setModelAssumptions(e.target.value)} placeholder={t("analyst.projects.modelAssumptions")} />
            <input value={modelSources} onChange={(e) => setModelSources(e.target.value)} placeholder={t("analyst.projects.modelSources")} />
            <input value={modelMissing} onChange={(e) => setModelMissing(e.target.value)} placeholder={t("analyst.projects.modelMissing")} />
            <button
              type="button"
              className="btn"
              disabled={
                busy ||
                !modelName.trim() ||
                !modelFigure.trim() ||
                !modelUnit.trim() ||
                !modelAssumptions.trim() ||
                !modelSources.trim() ||
                !modelMissing.trim() ||
                !companyId
              }
              data-testid="analyst-model-save"
              onClick={() =>
                void act(
                  () =>
                    postAnalystModel(project.project_id, {
                      company_id: companyId,
                      name: modelName.trim(),
                      figure: Number(modelFigure),
                      unit: modelUnit.trim(),
                      as_of: new Date().toISOString().slice(0, 10),
                      assumptions: modelAssumptions.trim(),
                      sources: modelSources.trim(),
                      not_found: modelMissing.trim(),
                    }),
                  () => {
                    setModelName("");
                    setModelFigure("");
                    setModelUnit("");
                    setModelAssumptions("");
                    setModelSources("");
                    setModelMissing("");
                    onChanged();
                  },
                )
              }
            >
              {t("analyst.projects.saveModel")}
            </button>
          </div>
          <h3>{t("analyst.projects.files")}</h3>
          <p className="muted analyst-small">{t("analyst.projects.filesLede")}</p>
          <ul className="doc-list">
            {project.uploads.map((u) => (
              <li key={u.upload_id}>
                {u.filename}{" "}
                <span className="muted analyst-small">
                  {t("analyst.projects.passages", { n: u.passages })} · {u.uploaded_at}
                </span>{" "}
                <button
                  type="button"
                  className="btn ghost small"
                  disabled={busy}
                  onClick={() => void act(() => deleteAnalystUpload(project.project_id, u.upload_id), () => onChanged())}
                >
                  {t("analyst.monitors.remove")}
                </button>
              </li>
            ))}
          </ul>
          <input
            type="file"
            accept=".pdf,.docx,.xlsx,.txt,.csv,.md"
            disabled={busy}
            data-testid="analyst-upload"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) void upload(f);
            }}
          />
          <div className="analyst-actions">
            <button
              type="button"
              className="btn ghost small"
              disabled={busy}
              onClick={() => {
                if (window.confirm(t("analyst.projects.confirmDelete", { name: project.name })))
                  void act(() => deleteAnalystProject(project.project_id), () => onChanged(""));
              }}
            >
              {t("analyst.projects.delete")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function MonitorsPanel({
  monitors,
  limit,
  skills,
  companies,
  companyId,
  projects,
  projectId,
  signedIn,
  onChanged,
}: {
  monitors: AnalystMonitor[];
  limit: number;
  skills: AnalystSkill[];
  companies: CompanySummary[];
  companyId: string;
  projects: AnalystProject[];
  projectId: string;
  signedIn: boolean;
  onChanged: () => void;
}) {
  const { t } = useI18n();
  const [scope, setScope] = useState<AnalystMonitorScope>("company");
  const [skillId, setSkillId] = useState("coverage_monitor");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const companyName = (id: string) => companies.find((c) => c.id === id)?.name || id;
  const projectName = (id: string) => projects.find((p) => p.project_id === id)?.name || id;
  const allSkills = skills;
  const shownSkills = scope === "project" ? allSkills : allSkills.filter((s) => !s.requires_project);
  const skillTitle = (id: string) => allSkills.find((s) => s.id === id)?.title || id;
  const ready = scope === "company" ? !!companyId : scope === "project" ? !!projectId : signedIn;
  const target = (m: AnalystMonitor) =>
    m.scope === "watchlist"
      ? t("analyst.monitors.scope.watchlistOf")
      : m.scope === "project"
        ? t("analyst.monitors.scope.projectOf", { name: projectName(m.project_id || "") })
        : companyName(m.company_id || "");
  const addLabel =
    scope === "company"
      ? t("analyst.monitors.add", { company: companyName(companyId) })
      : scope === "project"
        ? t("analyst.monitors.addProject", { name: projectId ? projectName(projectId) : "—" })
        : t("analyst.monitors.addWatchlist");

  useEffect(() => {
    if (!shownSkills.some((s) => s.id === skillId) && shownSkills[0]) setSkillId(shownSkills[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, skills]);

  async function add() {
    setBusy(true);
    setError(null);
    try {
      await postAnalystMonitor({
        skill_id: skillId,
        scope,
        company_id: scope === "company" ? companyId : undefined,
        project_id: scope === "project" ? projectId : undefined,
        email: email.trim() || undefined,
      });
      onChanged();
    } catch (e) {
      setError(errorText(e, t("analyst.monitors.err")));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await deleteAnalystMonitor(id);
      onChanged();
    } catch (e) {
      setError(errorText(e, t("analyst.monitors.err")));
    }
  }

  return (
    <section className="panel" data-testid="analyst-monitors">
      <div className="panel-head">
        <h2>{t("analyst.monitors.title")}</h2>
      </div>
      <p className="muted analyst-small">{t("analyst.monitors.lede", { limit })}</p>
      <div className="analyst-monitor-form">
        <label>
          {t("analyst.monitors.scope.label")}
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as AnalystMonitorScope)}
            data-testid="analyst-monitor-scope"
          >
            <option value="company">{t("analyst.monitors.scope.company")}</option>
            <option value="watchlist" disabled={!signedIn}>
              {t("analyst.monitors.scope.watchlist")}
            </option>
            <option value="project" disabled={projects.length === 0}>
              {t("analyst.monitors.scope.project")}
            </option>
          </select>
        </label>
        <label>
          {t("analyst.monitors.skill")}
          <select value={skillId} onChange={(e) => setSkillId(e.target.value)} data-testid="analyst-monitor-skill">
            {shownSkills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("analyst.monitors.email")}
          <input
            type="email"
            value={email}
            placeholder={t("analyst.monitors.emailPlaceholder")}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="btn-primary"
          disabled={busy || !ready}
          onClick={() => void add()}
          data-testid="analyst-monitor-add"
        >
          {addLabel}
        </button>
      </div>
      {scope === "project" && !projectId && (
        <p className="muted analyst-small">{t("analyst.monitors.pickProject")}</p>
      )}
      {error && <p className="error">{error}</p>}
      {monitors.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>{t("analyst.monitors.company")}</th>
              <th>{t("analyst.monitors.skill")}</th>
              <th>{t("analyst.monitors.delivery")}</th>
              <th>{t("analyst.monitors.last")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {monitors.map((m) => (
              <tr key={m.monitor_id}>
                <td>{target(m)}</td>
                <td>{skillTitle(m.skill_id)}</td>
                <td>{m.email || t("analyst.monitors.feedOnly")}</td>
                <td>{m.last_triggered_at || t("analyst.monitors.never")}</td>
                <td>
                  <button type="button" className="btn ghost small" onClick={() => void remove(m.monitor_id)}>
                    {t("analyst.monitors.remove")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default function AnalystPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const canAdmin = user?.role === "owner" || user?.role === "admin";
  const [params, setParams] = useSearchParams();
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [skills, setSkills] = useState<AnalystSkill[]>([]);
  const [run, setRun] = useState<AnalystRun | null>(null);
  const [history, setHistory] = useState<AnalystRunSummary[]>([]);
  const [feed, setFeed] = useState<AnalystRunSummary[]>([]);
  const [monitors, setMonitors] = useState<AnalystMonitor[]>([]);
  const [projects, setProjects] = useState<AnalystProject[]>([]);
  const [projectId, setProjectId] = useState("");
  const [monitorLimit, setMonitorLimit] = useState(0);
  const [commitments, setCommitments] = useState<CommitmentView | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function loadProjects(selectId?: string) {
    fetchAnalystProjects()
      .then((r) => {
        setProjects(r.projects);
        if (selectId !== undefined) setProjectId(selectId);
      })
      .catch(() => undefined);
  }

  function loadMonitors() {
    fetchAnalystMonitors()
      .then((m) => {
        setMonitors(m.monitors);
        setMonitorLimit(m.limit);
      })
      .catch(() => undefined);
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchCompanies({ limit: 50 }), fetchAnalystSkills(), fetchAnalystRuns(), fetchAnalystFeed()])
      .then(([rows, sk, runs, fd]) => {
        if (cancelled) return;
        setCompanies(rows);
        if (rows[0]) setCompanyId(rows[0].id);
        setSkills(sk.skills);
        setHistory(runs.runs);
        setFeed(fd.runs);
      })
      .catch((e) => !cancelled && setError(errorText(e, t("analyst.err.load"))));
    loadMonitors();
    loadProjects();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runParam = params.get("run");
  useEffect(() => {
    if (!runParam) return;
    let cancelled = false;
    fetchAnalystRun(runParam)
      .then((r) => !cancelled && setRun(r))
      .catch((e) => !cancelled && setError(errorText(e, t("analyst.err.run"))));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runParam]);

  useEffect(() => {
    if (!companyId) return;
    let cancelled = false;
    fetchCompanyCommitments(companyId)
      .then((v) => !cancelled && setCommitments(v))
      .catch(() => !cancelled && setCommitments(null));
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  async function runSkill(skillId: string) {
    if (!companyId) return;
    setBusy(skillId);
    setError(null);
    try {
      const out = await postAnalystRun({
        skill_id: skillId,
        company_id: companyId,
        project_id: projectId || undefined,
      });
      setRun(out);
      if (runParam) setParams({});
      fetchAnalystRuns().then((r) => setHistory(r.runs)).catch(() => undefined);
    } catch (e) {
      setError(errorText(e, t("analyst.err.run")));
    } finally {
      setBusy(null);
    }
  }

  function openRun(runId: string) {
    setError(null);
    setParams({ run: runId });
  }

  return (
    <PlanAccessGate
      feature="analyst_agent"
      title={t("analyst.title")}
      kicker={t("analyst.kicker")}
      description={t("analyst.lede")}
      returnTo="/analyst"
      testId="analyst-access-gate"
    >
      <section className="analyst-page" data-testid="analyst-page">
        <p className="page-kicker">{t("analyst.kicker")}</p>
        <h1>{t("analyst.title")}</h1>
        <p className="muted lede">{t("analyst.lede")}</p>

        <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} testId="analyst-company" />
        {error && <p className="error">{error}</p>}

        <ProjectsPanel
          projects={projects}
          projectId={projectId}
          companyId={companyId}
          companyName={companies.find((c) => c.id === companyId)?.name || companyId}
          onSelect={setProjectId}
          onChanged={loadProjects}
        />

        <section className="panel">
          <div className="panel-head">
            <h2>{t("analyst.skills")}</h2>
          </div>
          <div data-testid="analyst-skill-groups">
            {groupAnalystSkills(skills).map((group) => {
              return (
                <div key={group.title}>
                  <h3>{group.title}</h3>
                  <ul className="analyst-skills">
                    {group.skills.map((s) => (
                      <li key={s.id}>
                        <div>
                          <strong>{s.title}</strong>
                          <p className="muted analyst-small">{s.description}</p>
                        </div>
                        <button
                          type="button"
                          className="btn-primary"
                          disabled={!!busy || !companyId || (!!s.requires_project && !projectId)}
                          title={s.requires_project && !projectId ? t("analyst.projects.needsProject") : undefined}
                          onClick={() => void runSkill(s.id)}
                          data-testid={`analyst-run-${s.id}`}
                        >
                          {busy === s.id ? t("analyst.running") : t("analyst.run")}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </section>

        {run && <RunOutput run={run} />}
        {commitments && <CommitmentPanel view={commitments} />}

        <MonitorsPanel
          monitors={monitors}
          limit={monitorLimit}
          skills={skills}
          companies={companies}
          companyId={companyId}
          projects={projects}
          projectId={projectId}
          signedIn={!!user}
          onChanged={loadMonitors}
        />
        <DigestPanel />

        <section className="panel" data-testid="analyst-feed">
          <div className="panel-head">
            <h2>{t("analyst.feed.title")}</h2>
          </div>
          {feed.length === 0 ? (
            <p className="muted analyst-small">{t("analyst.feed.empty")}</p>
          ) : (
            <ul className="doc-list">
              {feed.slice(0, 20).map((h) => (
                <li key={h.run_id}>
                  <button type="button" className="btn ghost small" onClick={() => openRun(h.run_id)}>
                    {h.company_name} · {h.trigger?.title || h.skill_title}
                  </button>{" "}
                  <span className="muted analyst-small">
                    {h.skill_title} · {h.trigger?.date || h.generated_at}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {history.length > 0 && (
          <section className="panel">
            <div className="panel-head">
              <h2>{t("analyst.history")}</h2>
            </div>
            <ul className="doc-list">
              {history.slice(0, 15).map((h) => (
                <li key={h.run_id}>
                  <button type="button" className="btn ghost small" onClick={() => openRun(h.run_id)}>
                    {h.skill_title} · {h.company_name}
                  </button>{" "}
                  <span className="muted analyst-small">{h.generated_at}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <h2 className="analyst-settings-head" data-testid="analyst-settings">{t("analyst.settings.title")}</h2>
        <p className="muted analyst-small">
          {canAdmin ? t("analyst.settings.ledeAdmin") : t("analyst.settings.ledeMember")}
        </p>
        <HouseStylePanel canEdit={canAdmin} />
        {canAdmin && <DestinationsPanel />}
        {canAdmin && <KeysPanel />}
      </section>
    </PlanAccessGate>
  );
}
