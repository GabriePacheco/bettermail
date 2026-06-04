import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlignLeft,
  Briefcase,
  FileText,
  Gem,
  Mail,
  Shield,
  Smile,
  Sparkles,
  Sun,
  User,
} from "lucide-react";

import { getUsageStatus, rewriteEmail } from "../api/bettermailApi";
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
    originalText,
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
  const [usage, setUsage] = useState({
    used: 0,
    limit: 0,
    remaining: 0,
    status: "loading",
  });
  const autoRewriteTextRef = useRef("");

  const canRun = useMemo(
    () => isMeaningfulText(draftText) || (isReply && isMeaningfulText(quotedText)),
    [draftText, isReply, quotedText]
  );
  const hasImproved = useMemo(() => !!improvedText?.trim(), [improvedText]);

  const getRewritePayload = useCallback(() => {
    if (isMeaningfulText(draftText)) {
      return {
        mode: "rewrite_draft",
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

  const handleRewrite = useCallback(async () => {
    const payload = getRewritePayload();

    if (!payload) {
      setInfoMessage("Escribe un texto en el correo para poder mejorarlo.");
      return;
    }

    try {
      setLoading(true);
      setActionError("");
      setInfoMessage("");

      const data = await rewriteEmail({
        text: payload.text,
        tone: selectedTone,
        user: userProfile,
        mode: payload.mode,
        context: payload.context,
      });

      setImprovedText(data.improvedText || "");
      setLastRewriteMode(payload.mode);

      if (data.usage) {
        setUsage(data.usage);
      }
    } catch (err) {
      setActionError(err.message || "No se pudo reescribir el correo.");
    } finally {
      setLoading(false);
    }
  }, [getRewritePayload, selectedTone, userProfile]);

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
    if (!isReady || !canRun || loading || improvedText.trim()) return;

    const autoRewriteKey = `${draftText}:${quotedText}`;
    if (autoRewriteTextRef.current === autoRewriteKey) return;

    autoRewriteTextRef.current = autoRewriteKey;
    handleRewrite();
  }, [canRun, draftText, handleRewrite, improvedText, isReady, loading, quotedText]);

  const handleReplace = async () => {
    try {
      setActionError("");
      await replaceDraftWithText(improvedText);
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
    } catch (err) {
      setActionError(err.message || "No se pudo actualizar.");
    }
  };

  const handleToneChange = (tone) => {
    setSelectedTone(tone);
    setImprovedText("");
    autoRewriteTextRef.current = `${draftText}:${quotedText}`;
  };

  const originalHelperText = useMemo(() => {
    if (isMeaningfulText(draftText)) {
      return "Solo se procesará tu texto, no el historial del correo.";
    }

    if (isReply && isMeaningfulText(quotedText)) {
      return "No has escrito una respuesta todavía. Puedo sugerirte una respuesta usando el contexto del correo anterior.";
    }

    return "Escribe un texto en el correo para poder mejorarlo.";
  }, [draftText, isReply, quotedText]);

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
          title="Original"
          badge={
            <button
              type="button"
              onClick={handleRefreshFromOutlook}
              className="refresh-badge"
            >
              <Mail size={14} />
              Desde Outlook
            </button>
          }
          icon={FileText}
          value={originalText}
          readOnly
          helperText={originalHelperText}
        />

        <EmailCard
          title="Mejorado"
          badge="Generado por IA"
          icon={Sparkles}
          value={improvedText}
          onChange={setImprovedText}
          readOnly={false}
          status="success"
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
          onRegenerate={handleRewrite}
        />

        <PlanFooter
          used={usage.used}
          limit={usage.limit}
          loading={usage.status === "loading"}
        />
      </div>
    </main>
  );
}
