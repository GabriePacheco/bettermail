import { Save, X } from "lucide-react";
import { useEffect, useState } from "react";

export default function CustomToneDialog({ initialValue, onClose, onSave }) {
  const [name, setName] = useState(initialValue?.name || "Mi tono");
  const [personality, setPersonality] = useState(initialValue?.personality || "");

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanPersonality = personality.trim();
    if (!cleanName || !cleanPersonality) return;
    onSave({ name: cleanName, personality: cleanPersonality });
  };

  return (
    <div className="tone-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="tone-dialog bm-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="custom-tone-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="tone-dialog-header">
          <h2 id="custom-tone-title">Mi tono</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">
            <X size={17} />
          </button>
        </header>

        <form className="tone-dialog-form" onSubmit={handleSubmit}>
          <label htmlFor="custom-tone-name">Nombre</label>
          <input
            id="custom-tone-name"
            value={name}
            maxLength={30}
            onChange={(event) => setName(event.target.value)}
            autoFocus
          />

          <label htmlFor="custom-tone-personality">Personalidad</label>
          <textarea
            id="custom-tone-personality"
            value={personality}
            maxLength={600}
            rows={5}
            onChange={(event) => setPersonality(event.target.value)}
          />

          <button
            type="submit"
            className="tone-dialog-save"
            disabled={!name.trim() || !personality.trim()}
          >
            <Save size={16} />
            Guardar
          </button>
        </form>
      </section>
    </div>
  );
}
