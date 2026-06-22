import { ArrowRight, CheckCircle2, Crown, Loader2, PieChart } from "lucide-react";

export default function PlanFooter({
  used = 0,
  limit = 0,
  loading = false,
  plan = "trial",
  status = "trial",
  upgradeRequired = false,
  checkoutLoading = false,
  proPlan,
  onUpgrade,
}) {
  const percentage = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const usageText = loading ? "Cargando..." : `${used}/${limit} usados`;
  const isPro = plan === "pro" && status === "active";
  const proPrice = proPlan ? `$${Number(proPlan.price).toFixed(2)}` : "Pro";
  const proSubtitle = isPro
    ? "Administrar plan"
    : upgradeRequired
      ? "Activar Pro"
      : `${proPrice}/mes`;

  return (
    <div className="footer-grid">
      <div className="plan-card bm-card">
        <div className="plan-card-info">
          <div className="plan-card-icon">
            <PieChart size={18} />
          </div>
          <div className="plan-card-copy">
            <p className="plan-card-title">
              <span className="plan-title-full">
                {isPro ? "Uso mensual Pro" : "Uso del trial"}
              </span>
              <span className="plan-title-compact">Uso</span>
            </p>
            <p className="plan-card-text">{usageText}</p>
          </div>
        </div>

        <div className="plan-card-track" aria-label={`${percentage}% utilizado`}>
          <div className="plan-card-progress" style={{ width: `${percentage}%` }} />
        </div>
      </div>

      <button
        type="button"
        className={`pro-card ${isPro ? "pro-card-active" : ""}`}
        disabled={loading || checkoutLoading}
        onClick={onUpgrade}
      >
        <div className="pro-card-icon">
          {isPro ? <CheckCircle2 size={16} /> : <Crown size={16} />}
        </div>
        <div className="pro-card-copy">
          <p className="pro-card-title">{isPro ? "BetterMail Pro" : "Hazte Pro"}</p>
          <p className="pro-card-subtitle">{checkoutLoading ? "Abriendo..." : proSubtitle}</p>
        </div>
        {checkoutLoading ? (
          <Loader2 size={18} className="pro-card-arrow spin-icon" />
        ) : (
          <ArrowRight size={18} className="pro-card-arrow" />
        )}
      </button>

      <div className="app-version">v1.0.10</div>
    </div>
  );
}
