import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlignLeft,
  Briefcase,
  CheckCircle2,
  Gem,
  Mail,
  RefreshCw,
  Shield,
  Smile,
  Sparkles,
  Sun,
  User,
} from "lucide-react";

import {
  getPlans,
  getPricingUrl,
  getUsageStatus,
  rewriteEmail,
} from "../api/bettermailApi";
import ActionButtons from "../components/ActionButtons";
import EmailCard from "../components/EmailCard";
import PlanFooter from "../components/PlanFooter";
import TonePills from "../components/TonePills";
import { useOfficeEmail } from "../hooks/useOfficeEmail";
import { useOfficeTheme } from "../hooks/useOfficeTheme";
import {
  isMeaningfulText,
  limitText,
} from "../utils/emailHtml";

const toneOptions = [
  { value: "profesional", label: "Profesional", compactLabel: "Pro", icon: Briefcase },
  { value: "institucional", label: "Claro", compactLabel: "Claro", icon: Sun },
  { value: "conciliador", label: "Amable", compactLabel: "Amable", icon: Smile },
  { value: "firme_amable", label: "Firme", compactLabel: "Firme", icon: Shield },
  { value: "ejecutivo", label: "Ejecutivo", compactLabel: "Ejec.", icon: User },
  { value: "directo", label: "Breve", compactLabel: "Breve", icon: AlignLeft },
  { value: "diplomatico", label: "Elegante", compactLabel: "Eleg.", icon: Gem },
];

export default function Taskpane() {
  useOfficeTheme();

  const {
    draftText,
    quotedText,
    isReply,
    isReady,
    error,
    isPreviewMode,
    userProfile,
    refreshEmail,
    replaceDraftWithText,
    insertBelowDraftText,
    copyText,
  } = useOfficeEmail();

  const [selectedTone, setSelectedTone] = useState("profesional");
  const [improvedText, setImprovedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [lastRewriteMode, setLastRewriteMode] = useState("rewrite_draft");
  const [plans, setPlans] = useState([]);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [usage, setUsage] = useState({
    used: 0,
    limit: 0,
    remaining: 0,
    plan: "trial",
    status: "loading",
    upgradeRequired: false,
  });
  const autoRewriteTextRef = useRef("");
  const lastSourcePayloadRef = useRef(null);
  const variationRef = useRef(0);
  const proPlan = useMemo(
    () => plans.find((plan) => plan.id === "pro_monthly"),
    [plans]
  );

  const canRun = useMemo(
    () => isMeaningfulText(draftText) || (isReply && isMeaningfulText(quotedText)),
    [draftText, isReply, quotedText]
  );
  const hasImproved = useMemo(() => !!improvedText?.trim(), [improvedText]);

  const getRewritePayload = useCallback(() => {
    if (isMeaningfulText(draftText)) {
      return {
        mode: isReply ? "rewrite_draft" : "compose_email",
        text: draftText,
        context: undefined,
      };
    }

    if (isReply && isMeaningfulText(quotedText)) {
      return {
        mode: "suggest_reply",
        text: "",
        context: limitText(quotedText),
      };
    }

    return null;
  }, [draftText, isReply, quotedText]);

  const compactOutlookStatus = useMemo(() => {
    if (isMeaningfulText(draftText)) {
      return {
        type: "success",
        text: "Texto detectado desde Outlook",
        detail: draftText,
      };
    }

    if (isReply && isMeaningfulText(quotedText)) {
      return {
        type: "context",
        text: "Puedo sugerirte una respuesta usando el contexto del correo anterior.",
        detail: quotedText,
      };
    }

    return {
      type: "empty",
      text: "Escribe un texto en Outlook para poder mejorarlo.",
      detail: "",
    };
  }, [draftText, isReply, quotedText]);

  const handleRewrite = useCallback(async ({ regenerate = false } = {}) => {
    const payload = regenerate
      ? lastSourcePayloadRef.current || getRewritePayload()
      : getRewritePayload();

    if (!payload) {
      setInfoMessage("Escribe un texto en el correo para poder mejorarlo.");
      return;
    }

    try {
      setLoading(true);
      setActionError("");
      setInfoMessage("");

      const variation = regenerate ? variationRef.current + 1 : 0;
      const data = await rewriteEmail({
        text: payload.text,
        tone: selectedTone,
        user: userProfile,
        mode: payload.mode,
        context: payload.context,
        variation,
      });

      setImprovedText(data.improvedText || "");
      setLastRewriteMode(payload.mode);
      lastSourcePayloadRef.current = payload;
      variationRef.current = variation;

      if (data.usage) {
        setUsage(data.usage);
      }
    } catch (err) {
      if (err.usage) {
        setUsage(err.usage);
      }
      setActionError(err.message || "No se pudo reescribir el correo.");
    } finally {
      setLoading(false);
    }
  }, [getRewritePayload, selectedTone, userProfile]);

  const handleRegenerate = useCallback(() => {
    handleRewrite({ regenerate: true });
  }, [handleRewrite]);

  const refreshUsage = useCallback(async () => {
    if (!userProfile?.email) return;

    const usageStatus = await getUsageStatus({ user: userProfile });
    setUsage(usageStatus);
  }, [userProfile]);

  useEffect(() => {
    if (!userProfile?.email) return;

    let cancelled = false;

    const loadUsage = async () => {
      try {
        const usageStatus = await getUsageStatus({ user: userProfile });
        if (!cancelled) {
          setUsage(usageStatus);
        }
      } catch {
        if (!cancelled) {
          setUsage((current) => ({ ...current, status: "unavailable" }));
        }
      }
    };

    loadUsage();

    return () => {
      cancelled = true;
    };
  }, [userProfile]);

  useEffect(() => {
    let cancelled = false;

    const loadPlans = async () => {
      try {
        const planList = await getPlans();
        if (!cancelled) {
          setPlans(planList);
        }
      } catch {
        if (!cancelled) {
          setPlans([]);
        }
      }
    };

    loadPlans();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleFocus = () => {
      refreshUsage().catch(() => {
        setUsage((current) => ({ ...current, status: "unavailable" }));
      });
    };

    window.addEventListener("focus", handleFocus);

    return () => {
      window.removeEventListener("focus", handleFocus);
    };
  }, [refreshUsage]);

  useEffect(() => {
    if (!isReady || !canRun || loading || improvedText.trim()) return;

    const autoRewriteKey = `${draftText}:${quotedText}`;
    if (autoRewriteTextRef.current === autoRewriteKey) return;

    autoRewriteTextRef.current = autoRewriteKey;
    handleRewrite();
  }, [canRun, draftText, handleRewrite, improvedText, isReady, loading, quotedText]);

  const handleReplace = async () => {
    try {
      setActionError("");
      await replaceDraftWithText(improvedText, lastRewriteMode);
    } catch (err) {
      setActionError(err.message || "No se pudo reemplazar el contenido.");
    }
  };

  const handleInsertBelow = async () => {
    try {
      setActionError("");
      await insertBelowDraftText(improvedText, lastRewriteMode);
    } catch (err) {
      setActionError(err.message || "No se pudo insertar el texto.");
    }
  };

  const handleCopy = async () => {
    try {
      setActionError("");
      await copyText(improvedText);
    } catch {
      setActionError("No se pudo copiar el texto.");
    }
  };

  const handleRefreshFromOutlook = async () => {
    try {
      setActionError("");
      setInfoMessage("");
      await refreshEmail();
      setImprovedText("");
      autoRewriteTextRef.current = "";
      lastSourcePayloadRef.current = null;
      variationRef.current = 0;
    } catch (err) {
      setActionError(err.message || "No se pudo actualizar.");
    }
  };

  const handleToneChange = (tone) => {
    setSelectedTone(tone);
    setImprovedText("");
    autoRewriteTextRef.current = `${draftText}:${quotedText}`;
  };

  const handleUpgrade = async () => {
    if (!userProfile?.email) {
      setActionError("No se pudo identificar el usuario de Outlook.");
      return;
    }

    try {
      setCheckoutLoading(true);
      setActionError("");
      setInfoMessage("");
      const pricingUrl = getPricingUrl({
        email: userProfile.email,
        display_name: userProfile.display_name,
        account_type: userProfile.account_type,
        time_zone: userProfile.time_zone,
      });

      window.open(pricingUrl, "_blank", "noopener,noreferrer");
      setInfoMessage("Abrimos la pagina de planes. Cuando actives Pro, vuelve a esta ventana.");
    } catch {
      const fallbackUrl = getPricingUrl({ checkout_status: "unavailable" });
      window.open(fallbackUrl, "_blank", "noopener,noreferrer");
      setInfoMessage("Abrimos la pagina de planes. Completa el pago desde ahi.");
    } finally {
      setCheckoutLoading(false);
    }
  };

  return (
    <main className="bm-shell">
      <div className="bm-container">
        {isPreviewMode && <span className="preview-badge">Modo vista previa</span>}

        {error && !isPreviewMode && (
          <div className="status-banner status-banner-error">{error}</div>
        )}

        {!isReady && !error && !isPreviewMode && (
          <div className="status-banner">Cargando Outlook...</div>
        )}

        <TonePills
          options={toneOptions}
          value={selectedTone}
          onChange={handleToneChange}
        />

        <EmailCard
          title="Mejorado"
          icon={Sparkles}
          value={improvedText}
          onChange={setImprovedText}
          readOnly={false}
          status="success"
          headerAction={(
            <button
              type="button"
              onClick={handleRefreshFromOutlook}
              className="refresh-badge improved-refresh"
              title="Actualizar texto desde Outlook"
            >
              <RefreshCw size={14} />
              Actualizar
            </button>
          )}
          footer={(
            <div className={`email-source-footer email-source-${compactOutlookStatus.type}`}>
              {compactOutlookStatus.detail ? (
                <details className="email-source-details">
                  <summary>
                    {compactOutlookStatus.type === "success" ? (
                      <CheckCircle2 size={14} />
                    ) : (
                      <Mail size={14} />
                    )}
                    {compactOutlookStatus.type === "context"
                      ? "Ver contexto detectado"
                      : "Ver texto detectado"}
                  </summary>
                  <p>{limitText(compactOutlookStatus.detail, 280)}</p>
                </details>
              ) : (
                <div className="email-source-empty">
                  <Mail size={14} />
                  <span>{compactOutlookStatus.text}</span>
                </div>
              )}

              <span className="generated-indicator">
                <CheckCircle2 size={12} />
                Generado por IA
              </span>
            </div>
          )}
        />

        {actionError && (
          <div className="status-chip status-chip-error">{actionError}</div>
        )}

        {infoMessage && !actionError && (
          <div className="status-chip">{infoMessage}</div>
        )}

        <ActionButtons
          disabled={!hasImproved || loading}
          regenerateDisabled={!canRun || loading}
          loading={loading}
          onReplace={handleReplace}
          onInsertBelow={handleInsertBelow}
          onCopy={handleCopy}
          onRegenerate={handleRegenerate}
        />

        <PlanFooter
          used={usage.used}
          limit={usage.limit}
          loading={usage.status === "loading"}
          plan={usage.plan}
          status={usage.status}
          upgradeRequired={usage.upgradeRequired}
          checkoutLoading={checkoutLoading}
          proPlan={proPlan}
          onUpgrade={handleUpgrade}
        />
      </div>
    </main>
  );
}
