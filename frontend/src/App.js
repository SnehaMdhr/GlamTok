/**
 * App shell - GlamTok, Nepal TikTok Fashion Engagement Predictor
 *
 * Fixed sidebar + top header + routed pages:
 *   Predict · Descriptive · Diagnostic · Predictive ·
 *   Prescriptive · Posts · Businesses
 * Layout & styling live in App.css / index.css (design tokens).
 */

import { useState, useCallback, useEffect } from "react";
import "./App.css";
import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";
import PredictPage from "./pages/PredictPage";
import AnalysisPage from "./pages/AnalysisPage";
import PostsPage from "./pages/PostsPage";
import BusinessesPage from "./pages/BusinessesPage";

const PAGE_META = {
  predict: {
    eyebrow: "Overview",
    title: "Predict Engagement",
  },
  descriptive: {
    eyebrow: "Analytics",
    title: "Descriptive Analysis",
  },
  diagnostic: {
    eyebrow: "Analytics",
    title: "Diagnostic Analysis",
  },
  predictive: {
    eyebrow: "Analytics",
    title: "Predictive Analysis",
  },
  prescriptive: {
    eyebrow: "Analytics",
    title: "Prescriptive Analysis",
  },
  posts: {
    eyebrow: "Data",
    title: "Posts",
  },
  businesses: {
    eyebrow: "Data",
    title: "Businesses",
  }
};

const ANALYSIS_KEYS = ["descriptive", "diagnostic", "predictive", "prescriptive"];

export default function App() {
  const [selectedCell, setSelectedCell] = useState(null);
  const [mainTab, setMainTab]           = useState("predict");
  const [navOpen, setNavOpen]           = useState(false);
  const [dark, setDark]                 = useState(() => localStorage.getItem("tkp-theme") === "dark");

  // apply + persist the theme: `.dark` on <html> flips every CSS token
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("tkp-theme", dark ? "dark" : "light");
  }, [dark]);

  const toggleTheme = useCallback(() => setDark(d => !d), []);

  const handleCellClick = useCallback((d, h, s) => {
    setSelectedCell(prev => prev?.d === d && prev?.h === h ? null : { d, h, s });
  }, []);

  const navigate = useCallback(key => {
    setMainTab(key);
    setNavOpen(false);
  }, []);

  const meta = PAGE_META[mainTab] || PAGE_META.predict;

  const renderPage = () => {
    switch (mainTab) {
      case "predict":
        return <PredictPage selectedCell={selectedCell} onCellClick={handleCellClick} />;
      case "posts":
        return <PostsPage />;
      case "businesses":
        return <BusinessesPage />;
      default:
        // the four analysis sections
        return <AnalysisPage tab={ANALYSIS_KEYS.includes(mainTab) ? mainTab : "descriptive"} />;
    }
  };

  return (
    <div className="app">
      <div className={navOpen ? "sidebar open" : "sidebar"}>
        <Sidebar active={mainTab} onChange={navigate} dark={dark} onToggleTheme={toggleTheme} />
      </div>
      {navOpen && <div className="sidebar-backdrop" onClick={() => setNavOpen(false)} />}

      <div className="main">
        <Header meta={meta} onOpenNav={() => setNavOpen(true)} onNavigate={navigate} />

        <main className="content">
          {renderPage()}
        </main>

      </div>
    </div>
  );
}
