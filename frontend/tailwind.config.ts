import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111A",
        panel: "#0E1A24",
        mist: "#EDF4F7",
        teal: "#0FB7A7",
        gold: "#DAB66B",
        slate: "#7E91A3",
        danger: "#DE5B6D",
        warning: "#E7A63A",
        success: "#23B26D"
      },
      fontFamily: {
        sans: ["var(--font-manrope)"],
        mono: ["var(--font-mono)"]
      },
      boxShadow: {
        glow: "0 24px 80px rgba(7, 17, 26, 0.18)"
      },
      backgroundImage: {
        radial: "radial-gradient(circle at top, rgba(15,183,167,0.18), transparent 35%)"
      }
    }
  },
  plugins: []
};

export default config;
