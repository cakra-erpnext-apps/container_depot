<template>
	<div class="mx-auto w-full max-w-lg space-y-4 md:max-w-2xl">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div class="min-w-0">
				<h1 class="truncate text-xl font-extrabold tracking-tight text-gray-900">
					{{ labels.cleaningTitle }}
				</h1>
				<p v-if="header" class="truncate font-mono text-[11px] text-gray-500">{{ header.container_no }}</p>
			</div>
			<button v-if="header" class="oak-btn oak-btn-secondary px-3 py-2" @click="reset">
				<Icon name="x" :size="16" /> {{ labels.cleaningReset }}
			</button>
		</div>

		<!-- Step 1 — pick the container -->
		<section class="oak-card p-4 space-y-2">
			<label class="oak-label">{{ labels.containerNumber }}</label>
			<div class="flex gap-2">
				<input
					v-model="containerNo"
					class="oak-input uppercase"
					:placeholder="labels.cleaningContainerPlaceholder"
					@keyup.enter="doFetch"
				/>
				<button class="oak-btn oak-btn-primary shrink-0 px-4" :disabled="prefillRes.loading" @click="doFetch">
					<Icon v-if="prefillRes.loading" name="loader" :size="16" class="animate-spin" />
					<span v-else>{{ labels.eirFetch }}</span>
				</button>
			</div>
			<p v-if="fetchErr" class="text-sm text-red-600">{{ fetchErr }}</p>
		</section>

		<!-- Created/submitted confirmation -->
		<section v-if="submitted" class="oak-card border-leaf-200 bg-leaf-50 p-4 space-y-2">
			<p class="font-bold text-leaf-700">
				<Icon name="check-circle" :size="18" /> {{ labels.cleaningSubmitted }}
			</p>
			<p class="font-mono text-sm text-gray-700">{{ submitted.statement_id || submitted.name }}</p>
			<a :href="printUrl" target="_blank" rel="noopener" class="oak-btn oak-btn-secondary inline-flex px-3 py-2">
				<Icon name="printer" :size="16" /> {{ labels.cleaningPrint }}
			</a>
		</section>

		<template v-if="header && !submitted">
			<!-- Step 2 — tank header (read-only, from the Container master) -->
			<section class="oak-card p-4">
				<p class="oak-section-title mb-2">{{ labels.cleaningTankDetails }}</p>
				<dl class="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
					<div v-for="cell in headerCells" :key="cell.label" class="min-w-0">
						<dt class="text-xs text-gray-400">{{ cell.label }}</dt>
						<dd class="truncate font-medium text-gray-800">{{ cell.value || "—" }}</dd>
					</div>
				</dl>
				<p v-if="header.inspection" class="mt-2 font-mono text-[11px] text-gray-400">
					{{ labels.cleaningRefEir }}: {{ header.inspection }}
				</p>
			</section>

			<!-- Step 3 — the 12 cleanliness checks -->
			<section class="oak-card p-4 space-y-3">
				<p class="oak-section-title">{{ labels.cleaningChecklist }}</p>
				<div v-for="g in groups" :key="g.section" class="space-y-2">
					<p class="text-xs font-bold uppercase tracking-wide text-gray-400">{{ g.section }}</p>
					<div v-for="item in g.items" :key="item.item_code" class="rounded-xl border border-gray-100 p-2.5">
						<div class="flex items-center justify-between gap-2">
							<span class="min-w-0 flex-1 text-sm text-gray-800">{{ item.item_name }}</span>
							<div class="flex shrink-0 gap-1">
								<button
									v-for="opt in ['Yes', 'No']"
									:key="opt"
									class="oak-toggle px-3 py-1.5 text-sm"
									:class="item.result === opt ? 'oak-toggle-on' : 'oak-toggle-off'"
									@click="item.result = opt"
								>
									{{ opt === 'Yes' ? labels.cleaningYes : labels.cleaningNo }}
								</button>
							</div>
						</div>
						<input
							v-if="item.result === 'No'"
							v-model="item.note"
							class="oak-input mt-2 text-sm"
							:placeholder="labels.cleaningNote"
						/>
					</div>
				</div>
			</section>

			<!-- Step 4 — gas free reading -->
			<section class="oak-card p-4 space-y-2">
				<p class="oak-section-title">{{ labels.cleaningGasFree }}</p>
				<div class="grid grid-cols-2 gap-2">
					<button
						v-for="opt in ['Yes', 'No']"
						:key="opt"
						class="oak-toggle px-2 py-3"
						:class="gasFree === opt ? 'oak-toggle-on' : 'oak-toggle-off'"
						@click="gasFree = opt"
					>
						{{ opt === 'Yes' ? labels.cleaningYes : labels.cleaningNo }}
					</button>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<div>
						<label class="oak-label">{{ labels.cleaningO2 }}</label>
						<input v-model="o2" type="number" step="0.01" class="oak-input" inputmode="decimal" />
					</div>
					<div>
						<label class="oak-label">{{ labels.cleaningLel }}</label>
						<input v-model="lel" type="number" step="0.01" class="oak-input" inputmode="decimal" />
					</div>
				</div>
			</section>

			<!-- Step 5 — seal numbers -->
			<section class="oak-card p-4 space-y-2">
				<p class="oak-section-title">{{ labels.cleaningSeals }}</p>
				<div>
					<label class="oak-label">{{ labels.cleaningSealManhole }}</label>
					<input v-model="sealManhole" class="oak-input" />
				</div>
				<div>
					<label class="oak-label">{{ labels.cleaningSealAirline }}</label>
					<input v-model="sealAirline" class="oak-input" />
				</div>
				<div>
					<label class="oak-label">{{ labels.cleaningSealBottom }}</label>
					<input v-model="sealBottom" class="oak-input" />
				</div>
			</section>

			<!-- Step 6 — remarks -->
			<section class="oak-card p-4 space-y-2">
				<label class="oak-label">{{ labels.eirRemarks }}</label>
				<textarea v-model="remarks" rows="3" class="oak-input"></textarea>
			</section>

			<!-- Step 7 — surveyor signature -->
			<section class="oak-card p-4 space-y-2">
				<div class="flex items-center justify-between">
					<p class="oak-section-title">{{ labels.cleaningSignature }}</p>
					<button v-if="signatureUrl" type="button" class="oak-link text-sm" @click="startResign">
						{{ labels.cleaningResign }}
					</button>
				</div>
				<div v-if="signatureUrl && !signing">
					<img :src="signatureUrl" class="h-28 w-full rounded-xl border border-gray-200 bg-white object-contain" />
				</div>
				<div v-else>
					<canvas
						ref="sigCanvas"
						class="h-28 w-full touch-none rounded-xl border border-dashed border-gray-300 bg-white"
						@pointerdown="sigDown"
						@pointermove="sigMove"
						@pointerup="sigUp"
						@pointerleave="sigUp"
					></canvas>
					<div class="mt-1 flex items-center justify-between text-xs text-gray-400">
						<span v-if="sigUploading">{{ labels.cleaningUploading }}</span>
						<span v-else-if="sigErr" class="text-red-600">{{ sigErr }}</span>
						<span v-else>{{ labels.signHint }}</span>
						<button type="button" class="text-gray-600 underline underline-offset-2" @click="clearSignature">
							{{ labels.clear }}
						</button>
					</div>
				</div>
			</section>

			<!-- Submit -->
			<button
				class="oak-btn oak-btn-primary w-full py-3 text-base"
				:disabled="createRes.loading"
				@click="submit"
			>
				<Icon v-if="createRes.loading" name="loader" :size="18" class="animate-spin" />
				<span v-else>{{ labels.cleaningSubmit }}</span>
			</button>
		</template>
	</div>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from "vue"
import { createResource } from "frappe-ui"
import { labels } from "@/utils/labels"
import { toast } from "@/utils/toast"
import Icon from "@/components/Icon.vue"

const containerNo = ref("")
const header = ref(null)
const submitted = ref(null)
const fetchErr = ref("")

const checklist = ref([]) // master taxonomy (12 rows)
const rows = ref([]) // reactive per-item result/note state

const gasFree = ref("")
const o2 = ref("")
const lel = ref("")
const sealManhole = ref("")
const sealAirline = ref("")
const sealBottom = ref("")
const remarks = ref("")

const printUrl = computed(() =>
	submitted.value
		? `/api/method/frappe.utils.print_format.download_pdf?doctype=Cleaning%20Statement&name=${encodeURIComponent(
				submitted.value.name
		  )}&format=Cleaning%20Statement%20Format&no_letterhead=1`
		: "#"
)

// Checklist taxonomy (loaded once).
const mastersRes = createResource({
	url: "container_depot.ess.cleaning.cleaning_masters",
	method: "GET",
	auto: true,
	onSuccess(data) {
		checklist.value = data.checklist || []
		if (!remarks.value) remarks.value = data.default_remarks || ""
		buildRows()
	},
})

function buildRows() {
	rows.value = (checklist.value || []).map((i) => reactive({ ...i, result: "Yes", note: "" }))
}

const groups = computed(() => {
	const out = []
	let cur = null
	for (const r of rows.value) {
		if (!cur || cur.section !== r.section) {
			cur = { section: r.section, items: [] }
			out.push(cur)
		}
		cur.items.push(r)
	}
	return out
})

const headerCells = computed(() => {
	const h = header.value || {}
	return [
		{ label: labels.cleaningTankType, value: h.tank_type },
		{ label: labels.cleaningClient, value: h.client },
		{ label: labels.cleaningCapacity, value: h.capacity },
		{ label: labels.cleaningTare, value: h.tare },
		{ label: labels.cleaningMgw, value: h.mgw },
		{ label: labels.cleaningPrevCargo, value: h.previous_cargo },
		{ label: labels.cleaningMfgDate, value: h.date_of_manufacture },
		{ label: labels.cleaningLastTest, value: h.last_test_date },
	]
})

const prefillRes = createResource({
	url: "container_depot.ess.cleaning.cleaning_prefill",
	method: "GET",
	onSuccess(data) {
		header.value = data
		// Prefill seal numbers from the container's last-known values (editable).
		sealManhole.value = data.seal_manhole || ""
		sealAirline.value = data.seal_airline || ""
		sealBottom.value = data.seal_bottom_outlet || ""
		if (data.default_remarks && !remarks.value) remarks.value = data.default_remarks
		if (!rows.value.length) buildRows()
	},
	onError(err) {
		fetchErr.value = err?.messages?.[0] || err?.message || labels.error
	},
})

function doFetch() {
	fetchErr.value = ""
	const no = containerNo.value.trim().toUpperCase()
	if (!no) return
	submitted.value = null
	prefillRes.fetch({ container_no: no })
}

const createRes = createResource({
	url: "container_depot.ess.cleaning.cleaning_create",
	method: "POST",
	onSuccess(data) {
		submitted.value = data
		toast.success(labels.cleaningSubmitted, { title: data.statement_id || data.name })
	},
	onError(err) {
		toast.error(err?.messages?.[0] || err?.message || labels.error)
	},
})

function submit() {
	if (!header.value) return
	const results = rows.value.map((r) => ({
		item_code: r.item_code,
		result: r.result,
		note: r.note || undefined,
	}))
	createRes.fetch({
		container: header.value.container,
		inspection: header.value.inspection || undefined,
		gas_free: gasFree.value || undefined,
		o2_percent: o2.value !== "" ? o2.value : undefined,
		lel_percent: lel.value !== "" ? lel.value : undefined,
		seal_manhole: sealManhole.value || undefined,
		seal_airline: sealAirline.value || undefined,
		seal_bottom_outlet: sealBottom.value || undefined,
		remarks: remarks.value || undefined,
		signature: signatureUrl.value || undefined,
		results: JSON.stringify(results),
		submit: 1,
	})
}

function reset() {
	header.value = null
	submitted.value = null
	containerNo.value = ""
	fetchErr.value = ""
	gasFree.value = ""
	o2.value = ""
	lel.value = ""
	sealManhole.value = ""
	sealAirline.value = ""
	sealBottom.value = ""
	remarks.value = ""
	signatureUrl.value = ""
	signing.value = false
	buildRows()
}

// --- file upload + virtual signature pad (mirrors EirChecklist) --------------
async function uploadFile(file) {
	const fd = new FormData()
	fd.append("file", file, file.name)
	fd.append("is_private", 1)
	fd.append("folder", "Home")
	const res = await fetch("/api/method/upload_file", {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		body: fd,
	})
	if (!res.ok) throw new Error("upload failed")
	const data = await res.json()
	return data.message.file_url
}

const sigCanvas = ref(null)
const signatureUrl = ref("")
const signing = ref(false)
const sigUploading = ref(false)
const sigErr = ref("")
let sigCtx = null
let sigDrawing = false
let sigHasInk = false
let sigTimer = null

function sigCtxInit() {
	const c = sigCanvas.value
	if (!c) return null
	if (sigCtx && sigCtx.canvas === c) return sigCtx
	const ratio = window.devicePixelRatio || 1
	c.width = c.clientWidth * ratio
	c.height = c.clientHeight * ratio
	const ctx = c.getContext("2d")
	ctx.scale(ratio, ratio)
	ctx.lineWidth = 2
	ctx.lineCap = "round"
	ctx.lineJoin = "round"
	ctx.strokeStyle = "#111827"
	sigCtx = ctx
	return ctx
}

function sigPos(e) {
	const r = sigCanvas.value.getBoundingClientRect()
	return { x: e.clientX - r.left, y: e.clientY - r.top }
}

function sigDown(e) {
	const ctx = sigCtxInit()
	if (!ctx) return
	sigDrawing = true
	const p = sigPos(e)
	ctx.beginPath()
	ctx.moveTo(p.x, p.y)
	sigCanvas.value.setPointerCapture?.(e.pointerId)
}

function sigMove(e) {
	if (!sigDrawing || !sigCtx) return
	const p = sigPos(e)
	sigCtx.lineTo(p.x, p.y)
	sigCtx.stroke()
	sigHasInk = true
}

function sigUp() {
	if (!sigDrawing) return
	sigDrawing = false
	if (!sigHasInk) return
	if (sigTimer) clearTimeout(sigTimer)
	sigTimer = setTimeout(uploadSignature, 600)
}

async function uploadSignature() {
	const c = sigCanvas.value
	if (!c || !sigHasInk) return
	sigErr.value = ""
	sigUploading.value = true
	try {
		const blob = await new Promise((res) => c.toBlob(res, "image/png"))
		signatureUrl.value = await uploadFile(new File([blob], "cleaning-signature.png", { type: "image/png" }))
		signing.value = false
	} catch (e) {
		sigErr.value = labels.signatureError
	} finally {
		sigUploading.value = false
	}
}

function clearSignature() {
	if (sigTimer) clearTimeout(sigTimer)
	const ctx = sigCtxInit()
	if (ctx && sigCanvas.value) ctx.clearRect(0, 0, sigCanvas.value.width, sigCanvas.value.height)
	sigHasInk = false
	signatureUrl.value = ""
}

function startResign() {
	signatureUrl.value = ""
	signing.value = true
	sigHasInk = false
	sigCtx = null
	nextTick(sigCtxInit)
}
</script>
