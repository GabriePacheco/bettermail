import { useMemo, useState } from "react";
import {
  Ban,
  CalendarX2,
  ChartNoAxesCombined,
  CheckCircle2,
  Crown,
  KeyRound,
  Loader2,
  LockKeyhole,
  RefreshCw,
  Search,
  ShieldCheck,
  Unlock,
  UserRound,
  XCircle,
} from "lucide-react";

import {
  activateAdminUser,
  blockAdminUser,
  cancelAdminUser,
  expireAdminUser,
  findAdminUser,
  getOpenAICosts,
  unblockAdminUser,
} from "../api/adminApi";

const BRAND_MARK = `${import.meta.env.BASE_URL}addin-icons/icon-64.png`;

function formatDate(value) {
  if (!value) return "No disponible";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No disponible";
  return new Intl.DateTimeFormat("es-EC", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function statusLabel(user) {
  if (user.status === "blocked") return "Bloqueado";
  if (user.subscriptionStatus === "past_due") return "Pago pendiente";
  if (user.subscriptionStatus === "cancel_pending") return "Cancelacion pendiente";
  if (user.subscriptionStatus === "expired") return "Expirado";
  if (user.plan === "pro" && user.status === "active") return "Pro activo";
  return "Trial";
}

function previewAdminUser() {
  if (!import.meta.env.DEV || !new URLSearchParams(window.location.search).has("preview_admin")) {
    return null;
  }
  return {
    exists: true,
    email: "demo@bettermailai.com",
    displayName: "Demo User",
    plan: "pro",
    status: "active",
    subscriptionStatus: "active",
    trialLimit: 24,
    trialUsed: 24,
    monthlyLimit: 300,
    monthlyUsed: 42,
    currentPeriodEnd: new Date(Date.now() + 14 * 86400000).toISOString(),
    cancelAtPeriodEnd: false,
    autoRenew: false,
    paymentActionRequired: false,
    renewalFailureCount: 0,
    paymentProvider: "payphone_cajita",
    hasReusablePaymentMethod: false,
    cardBrand: null,
    cardLastDigits: null,
    auditEvents: [
      {
        action: "manual_subscription_activated",
        createdAt: new Date().toISOString(),
        metadata: { reason: "Vista previa" },
      },
    ],
  };
}

export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");
  const [user, setUser] = useState(() => previewAdminUser());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [costs, setCosts] = useState(null);
  const [costLoading, setCostLoading] = useState(false);
  const normalizedEmail = email.trim().toLowerCase();
  const canSearch = Boolean(secret.trim() && normalizedEmail);
  const isBlocked = user?.status === "blocked";
  const hasActivePro = useMemo(
    () => user?.plan === "pro" && ["active", "cancel_pending", "past_due"].includes(user.subscriptionStatus),
    [user],
  );

  const runRequest = async (request, successMessage = "") => {
    if (!canSearch) return;
    try {
      setLoading(true);
      setError("");
      setNotice("");
      const result = await request({
        secret: secret.trim(),
        email: normalizedEmail,
        reason: reason.trim(),
      });
      setUser(result);
      setNotice(successMessage);
    } catch (err) {
      setError(err.message || "No se pudo completar la accion.");
    } finally {
      setLoading(false);
    }
  };

  const searchUser = (event) => {
    event?.preventDefault();
    runRequest(findAdminUser);
  };

  const confirmAction = (message, request, successMessage) => {
    if (!window.confirm(message)) return;
    runRequest(request, successMessage);
  };

  const loadCosts = async () => {
    if (!secret.trim()) return;
    try {
      setCostLoading(true);
      setError("");
      setCosts(await getOpenAICosts({ secret: secret.trim(), days: 30 }));
    } catch (err) {
      setError(err.message || "No se pudo consultar el costo de OpenAI.");
    } finally {
      setCostLoading(false);
    }
  };

  return (
    <main className="admin-shell">
      <header className="admin-header">
        <div className="admin-header-inner">
          <div className="admin-brand">
            <img src={BRAND_MARK} alt="" />
            <div>
              <strong>BetterMail AI</strong>
              <span>Administracion interna</span>
            </div>
          </div>
          <div className="admin-security"><LockKeyhole size={16} /> Acceso privado</div>
        </div>
      </header>

      <section className="admin-workspace">
        <aside className="admin-sidebar">
          <div className="admin-section-title">
            <ShieldCheck size={20} />
            <div><strong>Acceso</strong><span>La clave no se guarda.</span></div>
          </div>

          <label htmlFor="admin-secret">Clave administrativa</label>
          <div className="admin-input-row">
            <KeyRound size={17} />
            <input
              id="admin-secret"
              type="password"
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
              autoComplete="off"
              spellCheck="false"
            />
          </div>

          <form onSubmit={searchUser}>
            <label htmlFor="admin-email">Cuenta de Outlook</label>
            <div className="admin-input-row">
              <UserRound size={17} />
              <input
                id="admin-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="usuario@ejemplo.com"
                autoComplete="off"
              />
            </div>
            <button type="submit" className="admin-primary" disabled={!canSearch || loading}>
              {loading ? <Loader2 size={17} className="spin-icon" /> : <Search size={17} />}
              Consultar usuario
            </button>
          </form>

          <label htmlFor="admin-reason">Motivo de la accion</label>
          <textarea
            id="admin-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            maxLength={500}
            placeholder="Soporte, fraude, compensacion..."
          />
        </aside>

        <div className="admin-content">
          {error && <div className="admin-alert error"><XCircle size={18} />{error}</div>}
          {notice && <div className="admin-alert success"><CheckCircle2 size={18} />{notice}</div>}

          <section className="admin-costs">
            <div className="admin-costs-heading">
              <div><ChartNoAxesCombined size={19} /><span><strong>Costo de OpenAI</strong><small>Ultimos 30 dias</small></span></div>
              <button type="button" onClick={loadCosts} disabled={!secret.trim() || costLoading}>
                {costLoading ? <Loader2 size={16} className="spin-icon" /> : <RefreshCw size={16} />}
                Consultar
              </button>
            </div>
            {costs && (
              <div className="admin-cost-grid">
                <div><span>Costo estimado</span><strong>USD ${Number(costs.estimatedCostUsd).toFixed(4)}</strong></div>
                <div><span>Solicitudes</span><strong>{costs.requests}</strong></div>
                <div><span>Tokens totales</span><strong>{costs.totalTokens.toLocaleString("es-EC")}</strong></div>
                <div><span>Promedio</span><strong>USD ${costs.requests ? (costs.estimatedCostUsd / costs.requests).toFixed(5) : "0.00000"}</strong></div>
              </div>
            )}
          </section>

          {!user && (
            <div className="admin-empty">
              <Search size={30} />
              <h1>Consulta una cuenta</h1>
              <p>Ingresa la clave administrativa y el email exacto del usuario.</p>
            </div>
          )}

          {user && !user.exists && (
            <div className="admin-empty">
              <UserRound size={30} />
              <h1>Usuario no encontrado</h1>
              <p>{user.email}</p>
            </div>
          )}

          {user?.exists && (
            <>
              <section className="admin-user-header">
                <div>
                  <span className={`admin-status status-${user.status}`}>{statusLabel(user)}</span>
                  <h1>{user.displayName || "Usuario BetterMail"}</h1>
                  <p>{user.email}</p>
                </div>
                <button type="button" className="admin-icon-button" onClick={searchUser} disabled={loading} title="Actualizar">
                  <RefreshCw size={18} />
                </button>
              </section>

              <section className="admin-metrics">
                <div><span>Plan</span><strong>{user.plan === "pro" ? "BetterMail Pro" : "Trial"}</strong></div>
                <div><span>Uso</span><strong>{user.plan === "pro" ? `${user.monthlyUsed}/${user.monthlyLimit}` : `${user.trialUsed}/${user.trialLimit}`}</strong></div>
                <div><span>Vigencia</span><strong>{formatDate(user.currentPeriodEnd)}</strong></div>
                <div><span>Renovacion</span><strong>{user.autoRenew ? "Automatica" : "Manual"}</strong></div>
              </section>

              <section className="admin-actions">
                <h2>Acciones</h2>
                <div className="admin-action-grid">
                  <button type="button" onClick={() => confirmAction("¿Activar BetterMail Pro por 30 dias sin realizar un cobro?", activateAdminUser, "Pro activado manualmente.")} disabled={loading || hasActivePro}>
                    <Crown size={18} /><span><strong>Activar Pro</strong><small>30 dias, sin cobro</small></span>
                  </button>
                  {isBlocked ? (
                    <button type="button" onClick={() => confirmAction("¿Desbloquear este usuario?", unblockAdminUser, "Usuario desbloqueado.")} disabled={loading}>
                      <Unlock size={18} /><span><strong>Desbloquear</strong><small>Restaurar acceso</small></span>
                    </button>
                  ) : (
                    <button type="button" className="warning" onClick={() => confirmAction("¿Bloquear inmediatamente este usuario?", blockAdminUser, "Usuario bloqueado.")} disabled={loading}>
                      <Ban size={18} /><span><strong>Bloquear</strong><small>Suspender inmediatamente</small></span>
                    </button>
                  )}
                  <button type="button" onClick={() => confirmAction("¿Cancelar la renovacion al final del periodo?", cancelAdminUser, "Cancelacion programada.")} disabled={loading || !hasActivePro || !user.autoRenew || user.cancelAtPeriodEnd}>
                    <CalendarX2 size={18} /><span><strong>Cancelar renovacion</strong><small>Conservar periodo pagado</small></span>
                  </button>
                  <button type="button" className="danger" onClick={() => confirmAction("Esta accion expira Pro inmediatamente. ¿Continuar?", expireAdminUser, "Suscripcion expirada.")} disabled={loading || !hasActivePro}>
                    <XCircle size={18} /><span><strong>Expirar ahora</strong><small>Retirar Pro inmediatamente</small></span>
                  </button>
                </div>
              </section>

              <section className="admin-details">
                <h2>Facturacion</h2>
                <dl>
                  <div><dt>Estado</dt><dd>{user.subscriptionStatus || user.status}</dd></div>
                  <div><dt>Proveedor</dt><dd>{user.paymentProvider || "No disponible"}</dd></div>
                  <div><dt>Metodo reutilizable</dt><dd>{user.hasReusablePaymentMethod ? `${user.cardBrand || "Tarjeta"} •••• ${user.cardLastDigits || ""}` : "No"}</dd></div>
                  <div><dt>Intentos fallidos</dt><dd>{user.renewalFailureCount}</dd></div>
                </dl>
              </section>

              <section className="admin-audit">
                <h2>Auditoria reciente</h2>
                {user.auditEvents.length ? (
                  <div className="admin-audit-list">
                    {user.auditEvents.map((event, index) => (
                      <div key={`${event.action}-${event.createdAt || index}`}>
                        <strong>{event.action}</strong>
                        <span>{formatDate(event.createdAt)}</span>
                        {event.metadata.reason && <small>{event.metadata.reason}</small>}
                      </div>
                    ))}
                  </div>
                ) : <p className="admin-muted">Sin acciones administrativas registradas.</p>}
              </section>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
