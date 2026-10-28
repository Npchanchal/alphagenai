/** First screen after a sign-in that did not follow a bookmark. */

export function seatLanding(role?: string | null, companyScope?: string[] | null): string {
  const scope = (companyScope || []).map((id) => id.trim().toLowerCase()).filter(Boolean);
  switch ((role || "").toLowerCase()) {
    case "pm":
      return "/holdings";
    case "data":
      return "/developers";
    case "oversight":
      return "/org/settings?section=audit";
    case "ir":
      if (scope.length === 1) return `/companies/${scope[0]}`;
      if (scope.length > 1) return `/tracker?packed=${scope.join(",")}`;
      return "/tracker?ir=unnamed";
    case "analyst":
      return "/analyst";
    case "reviewer":
      return "/desk?tab=review";
    case "labeler":
      return "/desk?tab=labeling";
    default:
      return "/tracker";
  }
}

export const SEAT_COPY: Record<string, { label: string; sentence: string }> = {
  viewer: {
    label: "Viewer",
    sentence: "Reads the screener, the dossiers, and Filing Search.",
  },
  pm: {
    label: "Portfolio",
    sentence: "Reads the book and the screener. Cannot accept a figure onto the score.",
  },
  data: {
    label: "Data",
    sentence: "Reads the API and, on an Enterprise plan, downloads the file. Cannot accept a figure onto the score.",
  },
  ir: {
    label: "Investor relations",
    sentence: "Reads and exports a pack for the companies you name. Cannot accept a figure onto the score.",
  },
  oversight: {
    label: "Oversight",
    sentence: "Reads this organisation’s audit trail. Cannot accept a figure, invite a seat, or open billing.",
  },
  analyst: {
    label: "Analyst",
    sentence: "Runs notes and prepares rows. A reviewer accepts a row before it can enter the score.",
  },
  labeler: {
    label: "Labeler",
    sentence: "Marks outcomes in the labeling queue. Cannot accept a row.",
  },
  reviewer: {
    label: "Reviewer",
    sentence: "Accepts or sends back a row, and can do the analyst’s work.",
  },
  admin: {
    label: "Admin",
    sentence: "Invites seats and runs the desk. Cannot appoint another admin.",
  },
};

const SKILL_GROUPS: { title: string; ids: string[] }[] = [
  { title: "This print", ids: ["results_prep", "concall_questions", "coverage_monitor"] },
  { title: "Learn a name", ids: ["company_ramp", "company_note"] },
  {
    title: "Board, credit, and events",
    ids: [
      "board_scorecard",
      "peer_delivery_grid",
      "corporate_action_brief",
      "drhp_reader",
      "usfda_watch",
      "rating_tracker",
      "debate_map",
    ],
  },
];

/** Analyst home groups. A skill id not listed joins the last group, so a new skill file stays visible. */
export function groupAnalystSkills<T extends { id: string }>(skills: T[]): { title: string; skills: T[] }[] {
  const known = new Set(SKILL_GROUPS.flatMap((g) => g.ids));
  const last = SKILL_GROUPS.length - 1;
  return SKILL_GROUPS.map((group, index) => ({
    title: group.title,
    skills: skills.filter((s) => group.ids.includes(s.id) || (index === last && !known.has(s.id))),
  })).filter((group) => group.skills.length > 0);
}

export function canAcceptRole(role?: string | null): boolean {
  return ["reviewer", "admin", "owner"].includes((role || "").toLowerCase());
}
