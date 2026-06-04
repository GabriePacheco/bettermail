import { CheckCircle2 } from "lucide-react";
import { isValidElement } from "react";

export default function EmailCard({
  title,
  badge,
  icon: Icon,
  value,
  onChange,
  readOnly = true,
  status = "default",
  helperText = "",
}) {
  const isImproved = status === "success";
  const badgeIsElement = isValidElement(badge);
  const hasValue = !!value?.trim();

  return (
    <section className={`email-card bm-card ${isImproved ? "improved-card" : ""}`}>
      <div className="email-card-header">
        <div className="email-card-title">
          <span className="email-card-icon">
            <Icon size={18} />
          </span>
          {title}
        </div>

        {badge && badgeIsElement && badge}

        {badge && !badgeIsElement && (
          <div className={`email-card-badge ${isImproved ? "generated-badge" : ""}`}>
            {isImproved && <CheckCircle2 size={14} />}
            {badge}
          </div>
        )}
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        readOnly={readOnly}
        className={`email-textarea ${
          hasValue ? "email-textarea-filled" : "email-textarea-empty"
        }`}
        placeholder="Sin contenido..."
      />

      {helperText && <p className="email-card-helper">{helperText}</p>}
    </section>
  );
}
