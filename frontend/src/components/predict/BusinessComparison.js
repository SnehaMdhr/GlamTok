import { useState, useEffect } from "react";
import { API } from "../../api";
import BusinessBars from "../charts/BusinessBars";
import Dropdown from "../ui/Dropdown";

export default function BusinessComparison() {
  const [allBusinesses, setAllBusinesses] = useState([]);
  const [selected, setSelected]           = useState([]);
  const [scores, setScores]               = useState({});
  const [loading, setLoading]             = useState(true);

  useEffect(() => {
    fetch(`${API}/businesses?platform=tiktok`)
      .then(r => r.json())
      .then(d => {
        const list  = d.businesses || [];
        const names = list.map(b => b.business);
        const sc    = {};
        list.forEach(b => { sc[b.business] = b.avg_engagement_score ?? 0.03; });
        setAllBusinesses(names);
        setSelected(names.slice(0, 4));
        setScores(sc);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: "14px 0", fontSize: 13, color: "var(--text-muted)" }}>Loading businesses…</div>;

  const toggle = b => setSelected(prev => prev.includes(b) ? prev.filter(x => x !== b) : [...prev, b]);

  const items = selected.length
    ? selected.map(name => ({ name, score: scores[name] || 0 })).sort((a, b) => b.score - a.score)
    : allBusinesses.slice(0, 4).map(name => ({ name, score: scores[name] || 0 })).sort((a, b) => b.score - a.score);

  return (
    <>
      <div style={{ maxWidth: 300, marginBottom: 18, position: "relative" }}>
        <Dropdown
          label="businesses to compare" icon="building-store" multi selected={selected}
          display={selected.length ? `${selected.length} selected` : "Select businesses"}
          options={allBusinesses.map(b => ({ value: b, label: b }))}
          onChange={toggle} />
      </div>

      <BusinessBars items={items} nameWidth={96} />
    </>
  );
}
