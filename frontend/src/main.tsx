import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { I18nProvider } from "./i18n";
import { AuthProvider } from "./lib/auth";
import { EntitlementsProvider } from "./lib/entitlements";
import { TourProvider } from "./lib/TourProvider";
import { SourceViewerProvider } from "./lib/SourceViewerContext";
import "./fonts.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <I18nProvider>
        <AuthProvider>
          <EntitlementsProvider>
          <TourProvider>
            <SourceViewerProvider>
              <App />
            </SourceViewerProvider>
          </TourProvider>
          </EntitlementsProvider>
        </AuthProvider>
      </I18nProvider>
    </BrowserRouter>
  </StrictMode>,
);
