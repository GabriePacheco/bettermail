import { useEffect, useState } from "react";

const lightTheme = {
  mode: "light",
  bgApp: "#f8fafc",
  bgCard: "#ffffff",
  bgInput: "#ffffff",
  bgMuted: "#f1f5f9",
  textPrimary: "#111827",
  textSecondary: "#6b7280",
  border: "rgba(226, 232, 240, 0.9)",
  accent: "#2563eb",
  accentSoft: "#eff6ff",
  successBg: "#ecfdf5",
  successText: "#059669",
  proBg: "#fef3c7",
  shadow: "0 12px 30px rgba(15, 23, 42, 0.08)",
};

const darkTheme = {
  mode: "dark",
  bgApp: "#0f172a",
  bgCard: "#111827",
  bgInput: "#020617",
  bgMuted: "#1e293b",
  textPrimary: "#f8fafc",
  textSecondary: "#94a3b8",
  border: "#334155",
  accent: "#60a5fa",
  accentSoft: "#1e3a8a",
  successBg: "#0f2f1f",
  successText: "#86efac",
  proBg: "#312d18",
  shadow: "0 12px 30px rgba(0, 0, 0, 0.45)",
};

function hexToRgb(hex) {
  const cleaned = hex.replace("#", "");
  const full =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((c) => c + c)
          .join("")
      : cleaned;

  const num = parseInt(full, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function getBrightness(hex) {
  const { r, g, b } = hexToRgb(hex);
  return (r * 299 + g * 587 + b * 114) / 1000;
}

function readOfficeTheme() {
  try {
    const officeTheme = window.Office?.context?.officeTheme;
    if (!officeTheme) return null;

    const bg = officeTheme.bodyBackgroundColor || lightTheme.bgApp;
    const text = officeTheme.bodyForegroundColor || lightTheme.textPrimary;
    const accent = officeTheme.controlForegroundColor || lightTheme.accent;
    const isDark = getBrightness(bg) < 140;
    const base = isDark ? darkTheme : lightTheme;

    return {
      ...base,
      bgApp: bg,
      bgCard: isDark ? darkTheme.bgCard : lightTheme.bgCard,
      bgInput: isDark ? darkTheme.bgInput : lightTheme.bgInput,
      bgMuted: isDark ? darkTheme.bgMuted : lightTheme.bgMuted,
      textPrimary: text,
      textSecondary: isDark ? darkTheme.textSecondary : lightTheme.textSecondary,
      border: isDark ? darkTheme.border : lightTheme.border,
      accent,
      accentSoft: isDark ? darkTheme.accentSoft : lightTheme.accentSoft,
      successBg: isDark ? darkTheme.successBg : lightTheme.successBg,
      successText: isDark ? darkTheme.successText : lightTheme.successText,
      proBg: isDark ? darkTheme.proBg : lightTheme.proBg,
      shadow: isDark ? darkTheme.shadow : lightTheme.shadow,
    };
  } catch {
    return null;
  }
}

function applyTheme(theme) {
  const root = document.documentElement;

  root.setAttribute("data-theme", theme.mode);
  root.style.setProperty("--bm-bg-app", theme.bgApp);
  root.style.setProperty("--bm-bg-card", theme.bgCard);
  root.style.setProperty("--bm-bg-input", theme.bgInput);
  root.style.setProperty("--bm-bg-muted", theme.bgMuted);
  root.style.setProperty("--bm-text-primary", theme.textPrimary);
  root.style.setProperty("--bm-text-secondary", theme.textSecondary);
  root.style.setProperty("--bm-border", theme.border);
  root.style.setProperty("--bm-accent", theme.accent);
  root.style.setProperty("--bm-accent-soft", theme.accentSoft);
  root.style.setProperty("--bm-success-bg", theme.successBg);
  root.style.setProperty("--bm-success-text", theme.successText);
  root.style.setProperty("--bm-pro-bg", theme.proBg);
  root.style.setProperty("--bm-shadow", theme.shadow);
}

export function useOfficeTheme() {
  const [theme, setTheme] = useState(lightTheme);

  useEffect(() => {
    const syncTheme = () => {
      const officeTheme = readOfficeTheme();
      const nextTheme =
        officeTheme ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches
          ? darkTheme
          : lightTheme);

      setTheme(nextTheme);
      applyTheme(nextTheme);
    };

    syncTheme();

    let intervalId;

    if (window.Office && typeof window.Office.onReady === "function") {
      window.Office.onReady(() => {
        syncTheme();
        intervalId = window.setInterval(syncTheme, 1200);
      });
    } else {
      intervalId = window.setInterval(syncTheme, 1200);
    }

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onMediaChange = () => syncTheme();
    media.addEventListener?.("change", onMediaChange);

    return () => {
      if (intervalId) clearInterval(intervalId);
      media.removeEventListener?.("change", onMediaChange);
    };
  }, []);

  return theme;
}
