// Tiny global confirm-dialog bus for the Depot PWA. Import `confirm` anywhere and
// `await confirm({ title, message, confirmLabel })` — it resolves true if the user
// taps the confirm button, false otherwise. The single <ConfirmHost> mounted in
// App.vue renders the modal. Used to gate irreversible submits (a 2-step "Anda yakin?").
import { reactive } from "vue"

export const confirmState = reactive({
	open: false,
	title: "",
	message: "",
	confirmLabel: "",
	cancelLabel: "",
	danger: false,
	_resolve: null,
})

export function confirm(opts = {}) {
	return new Promise((resolve) => {
		confirmState.title = opts.title || "Konfirmasi"
		confirmState.message = opts.message || ""
		confirmState.confirmLabel = opts.confirmLabel || "Ya"
		confirmState.cancelLabel = opts.cancelLabel || "Batal"
		confirmState.danger = !!opts.danger
		confirmState._resolve = resolve
		confirmState.open = true
	})
}

export function resolveConfirm(value) {
	if (!confirmState.open) return
	confirmState.open = false
	const r = confirmState._resolve
	confirmState._resolve = null
	if (r) r(value)
}
