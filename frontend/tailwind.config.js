import frappeUIPreset from "frappe-ui/src/tailwind/preset"
import defaultTheme from "tailwindcss/defaultTheme"

export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {
			// OAK brand. `brand` = the orange sun (primary / identity), `leaf` = the
			// green island + wordmark (secondary / confirm). Anchored on the exact
			// logo hexes: brand-500 #F97828, leaf-600 #078044.
			colors: {
				brand: {
					50: "#FFF5ED",
					100: "#FFE7D4",
					200: "#FECBA6",
					300: "#FDAA6E",
					400: "#FB8A3F",
					500: "#F97828",
					600: "#EA6614",
					700: "#C2530F",
					800: "#9A4313",
					900: "#7C3913",
				},
				leaf: {
					50: "#ECFDF3",
					100: "#D2F5DF",
					200: "#A6ECC2",
					300: "#6DDD9D",
					400: "#33C476",
					500: "#12A957",
					600: "#078044",
					700: "#076838",
					800: "#08522F",
					900: "#073F27",
				},
			},
			fontFamily: {
				sans: ['"Plus Jakarta Sans Variable"', ...defaultTheme.fontFamily.sans],
			},
			boxShadow: {
				card: "0 1px 2px 0 rgb(16 24 40 / 0.04), 0 1px 3px 0 rgb(16 24 40 / 0.06)",
				soft: "0 8px 24px -8px rgb(16 24 40 / 0.12)",
				header: "0 1px 2px 0 rgb(16 24 40 / 0.05)",
			},
			screens: {
				standalone: {
					raw: "(display-mode: standalone)",
				},
			},
			padding: {
				"safe-top": "env(safe-area-inset-top)",
				"safe-bottom": "env(safe-area-inset-bottom)",
			},
			keyframes: {
				"fade-in": {
					"0%": { opacity: "0" },
					"100%": { opacity: "1" },
				},
				"slide-up": {
					"0%": { opacity: "0", transform: "translateY(8px)" },
					"100%": { opacity: "1", transform: "translateY(0)" },
				},
				shimmer: {
					"100%": { transform: "translateX(100%)" },
				},
			},
			animation: {
				"fade-in": "fade-in 0.2s ease-out",
				"slide-up": "slide-up 0.25s ease-out both",
			},
		},
	},
	plugins: [],
}
