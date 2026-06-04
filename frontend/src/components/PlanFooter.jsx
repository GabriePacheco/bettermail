import { ArrowRight, Crown, PieChart } from "lucide-react";

export default function PlanFooter({ used = 0, limit = 0, loading = false }) {
  const percentage = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const usageText = loading ? "Cargando..." : `${used}/${limit} usados`;

  return (
    <div className="footer-grid">
      <div className="plan-card bm-card">
        <div className="plan-card-info">
          <div className="plan-card-icon">
            <PieChart size={18} />
          </div>
          <div className="plan-card-copy">
            <p className="plan-card-title">
              <span className="plan-title-full">Uso del plan</span>
              <span className="plan-title-compact">Uso</span>
            </p>
            <p className="plan-card-text">{usageText}</p>
          </div>
        </div>

        <div className="plan-card-track" aria-label={`${percentage}% utilizado`}>
          <div className="plan-card-progress" style={{ width: `${percentage}%` }} />
        </div>
      </div>

      <button type="button" className="pro-card">
        <div className="pro-card-icon">
          <Crown size={16} />
        </div>
        <div className="pro-card-copy">
          <p className="pro-card-title">Hazte Pro</p>
          <p className="pro-card-subtitle">Mas funciones</p>
        </div>
        <ArrowRight size={18} className="pro-card-arrow" />
      </button>

      <div className="app-version">v1.0.10</div>
    </div>
  );
}
