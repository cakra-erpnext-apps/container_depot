import { computed, reactive } from "vue"

// Auth is the Frappe session cookie — there is no custom auth (PRD §3.3).
// The `user_id` cookie is set by Frappe on login; "Guest" means unauthenticated.
export function sessionUser() {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	let user = cookies.get("user_id")
	if (user === "Guest") user = null
	return user
}

// Send the browser through the standard Frappe login, returning to /depot.
export function redirectToLogin() {
	window.location.href = "/login?redirect-to=/depot"
}

export const session = reactive({
	user: sessionUser(),
	isLoggedIn: computed(() => !!session.user),
	logout() {
		// Frappe's /api/method/logout requires POST + a valid CSRF token (a plain GET
		// navigation 403s). Mirror the CSRF pattern used for uploads, then go to login.
		fetch("/api/method/logout", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		}).finally(() => {
			window.location.href = "/login?redirect-to=/depot"
		})
	},
})
