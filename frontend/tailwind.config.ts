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
        parchment: {
          50: "#F9F7F2",
          100: "#F2EFE9",
          200: "#E6E2D8",
          300: "#D9D2C5",
          400: "#C4BBAB",
        },
        gold: {
          50: "#FBF8EB",
          100: "#F5F0D6",
          200: "#EBDD98",
          300: "#C4A34A",
          400: "#A38332",
        },
        ink: {
          50: "#9B8E82",
          100: "#6B5E52",
          200: "#4A3F35",
          300: "#2C2520",
        },
      },
      fontFamily: {
        serif: ['"Noto Serif KR"', "serif"],
        sans: ['"IBM Plex Sans KR"', "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
