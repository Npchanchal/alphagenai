import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, Link } from "react-router-dom";
import BrandLogo from "./components/BrandLogo";
import SessionMenu from "./components/SessionMenu";
import SiteFooter from "./components/SiteFooter";
import SiteTour from "./components/SiteTour";
import TourWelcome from "./components/TourWelcome";
import LandingPage from "./pages/LandingPage";
import NotFoundPage from "./pages/NotFoundPage";
import RouteFallback from "./components/RouteFallback";
import RouteErrorBoundary from "./components/RouteErrorBoundary";
import PageAnalytics from "./components/PageAnalytics";
import ConsentBanner from "./components/ConsentBanner";
import SeoHead from "./components/SeoHead";
import { useAuth } from "./lib/auth";
import { useI18n } from "./i18n";
import AdminMenuBar from "./components/AdminMenuBar";
import NavMenu, { isWorkingRoute } from "./components/NavMenu";
import CommandPalette from "./components/CommandPalette";
import SightsLayout from "./pages/sights/SightsLayout";
import SightsHubPage from "./pages/sights/SightsHubPage";

const AboutPage = lazy(() => import("./pages/AboutPage"));
const MethodologyPage = lazy(() => import("./pages/MethodologyPage"));
const ChangelogPage = lazy(() => import("./pages/ChangelogPage"));
const CompanyDetailPage = lazy(() => import("./pages/CompanyDetailPage"));
const DeskPage = lazy(() => import("./pages/DeskPage"));
const HelpPage = lazy(() => import("./pages/HelpPage"));
const HomePage = lazy(() => import("./pages/HomePage"));
const CitationPage = lazy(() => import("./pages/CitationPage"));
const LegalPage = lazy(() => import("./pages/LegalPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const PilotRequestPage = lazy(() => import("./pages/PilotRequestPage"));
const PressPage = lazy(() => import("./pages/PressPage"));
const AnswersPage = lazy(() => import("./pages/AnswersPage"));
const ProductsPage = lazy(() => import("./pages/ProductsPage"));
const WorkflowsPage = lazy(() => import("./pages/WorkflowsPage"));
const DevelopersPage = lazy(() => import("./pages/DevelopersPage"));
const StatusPage = lazy(() => import("./pages/StatusPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const ResearchPage = lazy(() => import("./pages/ResearchPage"));
const AnalystPage = lazy(() => import("./pages/AnalystPage"));
const NinjaPage = lazy(() => import("./pages/NinjaPage"));
const HoldingsPage = lazy(() => import("./pages/HoldingsPage"));
const RankingsPage = lazy(() => import("./pages/RankingsPage"));
const AcceptInvitePage = lazy(() => import("./pages/AcceptInvitePage"));
const BillingPage = lazy(() => import("./pages/BillingPage"));
import AdminPortalPage from "./pages/AdminPortalPage";
const TrustPage = lazy(() => import("./pages/TrustPage"));
const BlogIndexPage = lazy(() => import("./pages/BlogIndexPage"));
const BlogPostPage = lazy(() => import("./pages/BlogPostPage"));
const SightsThemesPage = lazy(() =>
  import("./pages/sights/SightsEvidencePages").then((m) => ({
    default: m.SightsThemesPage,
  })),
);
const SightsStreetPage = lazy(() =>
  import("./pages/sights/SightsEvidencePages").then((m) => ({
    default: m.SightsStreetPage,
  })),
);
const SightsFieldPage = lazy(() =>
  import("./pages/sights/SightsEvidencePages").then((m) => ({
    default: m.SightsFieldPage,
  })),
);
const SightsGridPage = lazy(() =>
  import("./pages/sights/SightsAdvancedPages").then((m) => ({
    default: m.SightsGridPage,
  })),
);
const SightsDeepDivePage = lazy(() =>
  import("./pages/sights/SightsAdvancedPages").then((m) => ({
    default: m.SightsDeepDivePage,
  })),
);
const SightsFundamentalsPage = lazy(() =>
  import("./pages/sights/SightsAdvancedPages").then((m) => ({
    default: m.SightsFundamentalsPage,
  })),
);
const SightsSettingsPage = lazy(() =>
  import("./pages/sights/SightsAdvancedPages").then((m) => ({
    default: m.SightsSettingsPage,
  })),
);
const ForgotPasswordPage = lazy(() =>
  import("./pages/AuthRecoveryPages").then((m) => ({ default: m.ForgotPasswordPage })),
);
const ResetPasswordPage = lazy(() =>
  import("./pages/AuthRecoveryPages").then((m) => ({ default: m.ResetPasswordPage })),
);
const VerifyEmailPage = lazy(() =>
  import("./pages/AuthRecoveryPages").then((m) => ({ default: m.VerifyEmailPage })),
);
const AccountSettingsPage = lazy(() => import("./pages/AccountSettingsPage"));
const OrgSettingsPage = lazy(() => import("./pages/OrgSettingsPage"));

export default function App() {
  const { t } = useI18n();
  const { user, preferences } = useAuth();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const working = isWorkingRoute(location.pathname);
  const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform || "");

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.documentElement.dataset.density = preferences?.density || "compact";
  }, [preferences?.density]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setNavOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="app-shell">
      <SeoHead />
      <PageAnalytics />
      <a href="#main" className="skip-link">
        {t("app.skipToContent")}
      </a>
      <header className={working ? "topbar is-short" : "topbar"} data-frame={working ? "short" : "full"}>
        <div className="brand-block">
          <BrandLogo />
        </div>
        <button
          type="button"
          className="nav-toggle"
          aria-expanded={navOpen}
          aria-controls="primary-nav"
          data-testid="nav-toggle"
          onClick={() => setNavOpen((v) => !v)}
        >
          <span className="nav-toggle-bars" aria-hidden />
          {t("app.menu")}
        </button>
        <nav
          id="primary-nav"
          className={`topnav ${navOpen ? "open" : ""}`}
          aria-label={t("ui.App.primaryNav")}
        >
          <NavMenu working={working} />
          {working && (
            <button
              type="button"
              className="btn-ghost palette-hint"
              data-testid="palette-hint"
              title={t("palette.hintTitle")}
              onClick={() => document.dispatchEvent(new Event("citealpha:palette"))}
            >
              {t("palette.hint")} <kbd>{isMac ? "⌘K" : "Ctrl K"}</kbd>
            </button>
          )}
          <SessionMenu />
          {!working && <span className="compliance-micro">{t("compliance.micro")}</span>}
        </nav>
      </header>
      <AdminMenuBar />
      {user?.kind === "guest" && (
        <div className="guest-banner" data-testid="guest-banner">
          {t("guest.banner")}{" "}
          <Link to="/register">{t("common.register")}</Link>
        </div>
      )}
      <ConsentBanner />
      <main id="main" className="app-main">
        <RouteErrorBoundary>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/tracker" element={<HomePage />} />
            <Route path="/c/:citationId" element={<CitationPage />} />
            <Route path="/companies/:id" element={<CompanyDetailPage />} />
            <Route path="/desk" element={<DeskPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/analyst" element={<AnalystPage />} />
            <Route path="/holdings" element={<HoldingsPage />} />
            <Route path="/ninja" element={<NinjaPage />} />
            <Route path="/ninja/indices" element={<NinjaPage />} />
            <Route path="/ninja/tests" element={<NinjaPage />} />
            <Route path="/sights" element={<SightsLayout />}>
              <Route index element={<SightsHubPage />} />
              <Route path="search" element={<Navigate to="/research?scope=all" replace />} />
              <Route path="ask" element={<Navigate to="/research?tab=chat&scope=all" replace />} />
              <Route path="boards" element={<Navigate to="/research?tab=watch" replace />} />
              <Route path="themes" element={<SightsThemesPage />} />
              <Route path="street" element={<SightsStreetPage />} />
              <Route path="field" element={<SightsFieldPage />} />
              <Route path="grid" element={<SightsGridPage />} />
              <Route path="deep-dive" element={<SightsDeepDivePage />} />
              <Route path="fundamentals" element={<SightsFundamentalsPage />} />
              <Route path="agents" element={<Navigate to="/analyst" replace />} />
              <Route path="export" element={<Navigate to="/analyst" replace />} />
              <Route path="settings" element={<SightsSettingsPage />} />
            </Route>
            <Route path="/package" element={<Navigate to="/products#plans" replace />} />
            <Route path="/pilot" element={<PilotRequestPage />} />
            <Route path="/answers" element={<AnswersPage />} />
            <Route path="/methodology" element={<MethodologyPage />} />
            <Route path="/changelog" element={<ChangelogPage />} />
            <Route path="/press" element={<PressPage />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/workflows" element={<WorkflowsPage />} />
            <Route path="/developers" element={<DevelopersPage />} />
            <Route path="/status" element={<StatusPage />} />
            <Route path="/rankings" element={<RankingsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/about/tiers" element={<Navigate to="/products#features" replace />} />
            <Route path="/blog" element={<BlogIndexPage />} />
            <Route path="/blog/:slug" element={<BlogPostPage />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/accept-invite" element={<AcceptInvitePage />} />
            <Route path="/billing" element={<BillingPage />} />
            <Route path="/account" element={<AccountSettingsPage />} />
            <Route path="/org/settings" element={<OrgSettingsPage />} />
            <Route path="/admin" element={<AdminPortalPage />} />
            <Route path="/terms" element={<LegalPage />} />
            <Route path="/privacy" element={<LegalPage />} />
            <Route path="/trust" element={<TrustPage />} />
            <Route path="/404" element={<NotFoundPage />} />
            <Route path="*" element={<NotFoundPage path={location.pathname} />} />
          </Routes>
        </Suspense>
        </RouteErrorBoundary>
      </main>
      <SiteFooter />
      <TourWelcome />
      <SiteTour />
      <CommandPalette enabled={working} />
    </div>
  );
}
