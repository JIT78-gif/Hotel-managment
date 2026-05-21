import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: "#FAF5EE",
        parchment: "#F1E9DA",
        terracotta: {
          DEFAULT: "#C25B3E",
          dark: "#A2462D",
          light: "#E68B70"
        },
        forest: {
          DEFAULT: "#2F4A3B",
          light: "#4A6B59"
        },
        ink: "#1B1814",
        muted: "#6B5F52"
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-inter-tight)", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      boxShadow: {
        soft: "0 1px 2px rgba(27,24,20,0.06), 0 8px 24px rgba(27,24,20,0.05)",
        warm: "0 10px 30px rgba(194,91,62,0.18)"
      },
      borderRadius: {
        "2xl": "1.25rem",
        "3xl": "1.75rem"
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        pulse_dot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" }
        }
      },
      animation: {
        "fade-up": "fade-up 400ms cubic-bezier(0.22, 0.61, 0.36, 1) both",
        "pulse-dot": "pulse_dot 1.4s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;
