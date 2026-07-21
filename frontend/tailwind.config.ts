import type { Config } from "tailwindcss";

/**
 * Design tokens for Lumen.
 *
 * Palette rationale: a deep ink-navy (not pure black) reads as a research
 * workspace at night rather than a generic "dark mode app" default. The
 * warm gold accent (`glow`) is the one color that carries meaning — it is
 * used *only* for retention/recall states (fresh review streaks, active
 * citations), never for generic UI chrome, so it stays legible as a signal.
 * Cyan (`fresh`) marks newly-ingested content that hasn't been reviewed yet.
 */
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0B1120",
          soft: "#111827",
          deep: "#070B14",
        },
        glow: {
          DEFAULT: "#F2B84B",
          dim: "#8A6A2E",
        },
        fresh: {
          DEFAULT: "#5EEAD4",
          dim: "#2C6B63",
        },
        content: {
          primary: "#E8ECF4",
          muted: "#94A3B8",
          faint: "#5B6472",
        },
        glass: {
          DEFAULT: "rgba(255,255,255,0.04)",
          border: "rgba(255,255,255,0.08)",
          hover: "rgba(255,255,255,0.07)",
        },
      },
      fontFamily: {
        display: ["var(--font-source-serif)", "Georgia", "serif"],
        body: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      },
      backdropBlur: {
        xs: "2px",
      },
      boxShadow: {
        glow: "0 0 24px -6px rgba(242,184,75,0.35)",
        glass: "0 8px 32px -12px rgba(0,0,0,0.5)",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-glow": "pulse-glow 2.4s ease-in-out infinite",
        "fade-up": "fade-up 0.35s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
