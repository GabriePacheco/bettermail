import { ChevronLeft, ChevronRight, LockKeyhole, Settings2 } from "lucide-react";
import { useRef } from "react";

export default function TonePills({
  options,
  value,
  onChange,
  onConfigureCustom,
}) {
  const listRef = useRef(null);

  const scrollTones = (direction) => {
    listRef.current?.scrollBy({
      left: direction * 152,
      behavior: "smooth",
    });
  };

  return (
    <section className="tone-card bm-card">
      <div className="tone-card-header">
        <h2 className="tone-card-title">Tono predeterminado</h2>
        {value === "custom" && onConfigureCustom && (
          <button
            type="button"
            className="icon-button"
            onClick={onConfigureCustom}
            title="Editar mi tono"
            aria-label="Editar mi tono"
          >
            <Settings2 size={15} />
          </button>
        )}
      </div>

      <div className="tone-scroll-wrap">
        <button
          type="button"
          className="tone-scroll-button tone-scroll-left"
          onClick={() => scrollTones(-1)}
          aria-label="Ver tonos anteriores"
        >
          <ChevronLeft size={14} />
        </button>

        <div className="tone-list no-scrollbar" ref={listRef}>
          {options.map((item) => {
            const Icon = item.icon;
            const active = value === item.value;

            return (
              <button
                key={item.value}
                type="button"
                onClick={() => onChange(item.value)}
                className={`tone-button ${active ? "active" : ""}`}
                title={item.locked ? "Disponible con BetterMail Pro" : item.label}
              >
                <div className="tone-button-icon">
                  {item.locked ? <LockKeyhole size={16} /> : <Icon size={18} />}
                </div>
                <span className="tone-button-label tone-label-compact">
                  {item.compactLabel || item.label}
                </span>
                <span className="tone-button-label tone-label-full">{item.label}</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          className="tone-scroll-button tone-scroll-right"
          onClick={() => scrollTones(1)}
          aria-label="Ver más tonos"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </section>
  );
}
