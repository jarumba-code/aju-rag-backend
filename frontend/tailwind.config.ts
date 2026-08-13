import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          300: "#f0d060",
          400: "#d4af37",
          500: "#d4af37",
          600: "#b8962e",
        },
        aju: {
          navy: {
            DEFAULT: "#0a1628",
            light: "#0d2347",
            dark: "#06101c",
          },
          gold: {
            DEFAULT: "#d4af37",
            light: "#f0d060",
            dark: "#b8962e",
          },
          cream: "#f8f6f1",
          slate: {
            50: "#f8fafc",
            100: "#f1f5f9",
            200: "#e2e8f0",
            800: "#1e293b",
            900: "#0f172a",
          },
        },
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
      },
      boxShadow: {
        "aju-sm": "0 1px 2px 0 rgba(0,0,0,0.05)",
        "aju": "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)",
        "aju-lg": "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
        "aju-gold": "0 4px 14px 0 rgba(212,175,55,0.4)",
      },
    },
  },
  plugins: [],
};
export default config;
