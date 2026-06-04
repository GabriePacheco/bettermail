import { ArrowDownToLine, Copy, RefreshCcw, Replace } from "lucide-react";

export default function ActionButtons({
  disabled,
  regenerateDisabled,
  loading,
  onReplace,
  onInsertBelow,
  onCopy,
  onRegenerate,
}) {
  return (
    <div className="actions-grid">
      <button
        type="button"
        disabled={disabled}
        onClick={onReplace}
        className="action-button primary"
      >
        <Replace size={16} />
        <span>Reemplazar</span>
      </button>

      <button
        type="button"
        disabled={disabled}
        onClick={onInsertBelow}
        className="action-button secondary"
      >
        <ArrowDownToLine size={16} />
        <span>Poner debajo</span>
      </button>

      <button
        type="button"
        disabled={disabled}
        onClick={onCopy}
        className="action-button secondary"
      >
        <Copy size={16} />
        <span>Copiar</span>
      </button>

      <button
        type="button"
        disabled={regenerateDisabled}
        onClick={onRegenerate}
        className="action-button secondary"
      >
        <RefreshCcw size={16} className={loading ? "spin-icon" : ""} />
        <span>{loading ? "Generando..." : "Regenerar"}</span>
      </button>
    </div>
  );
}
