<template>
	<div class="mx-auto w-full max-w-lg space-y-4 md:max-w-2xl">
		<div class="flex items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<span class="oak-icon-tile h-9 w-9 bg-gray-100 text-gray-500"><Icon name="clock" :size="20" /></span>
				<h1 class="text-lg font-extrabold tracking-tight">{{ labels.eirHistoryTitle }}</h1>
			</div>
			<router-link to="/eir" class="oak-btn oak-btn-secondary shrink-0 px-3 py-2">
				<Icon name="clipboard" :size="16" /> {{ labels.eirTitle }}
			</router-link>
		</div>

		<div class="relative">
			<Icon
				name="search"
				:size="18"
				class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
			/>
			<input
				v-model="search"
				type="search"
				:placeholder="labels.eirHistorySearch"
				class="oak-input pl-10 uppercase"
				@input="onSearchInput"
			/>
		</div>

		<!-- Loading skeleton -->
		<ul v-if="history.loading && !items.length" class="oak-card divide-y divide-gray-100 overflow-hidden">
			<li v-for="n in 6" :key="n" class="flex items-center gap-3 px-4 py-3.5">
				<div class="oak-skeleton h-9 w-9 rounded-xl"></div>
				<div class="flex-1 space-y-2">
					<div class="oak-skeleton h-3.5 w-1/2"></div>
					<div class="oak-skeleton h-3 w-3/4"></div>
				</div>
			</li>
		</ul>

		<p v-else-if="history.error" class="flex items-center gap-2 text-sm text-red-600">
			<Icon name="alert-circle" :size="16" /> {{ labels.error }}
			<button class="oak-link" @click="history.reload()">{{ labels.retry }}</button>
		</p>

		<div v-else-if="!items.length" class="oak-card flex flex-col items-center gap-2 p-8 text-center">
			<span class="oak-icon-tile h-12 w-12 bg-gray-100 text-gray-300"><Icon name="inbox" :size="24" /></span>
			<p class="text-sm text-gray-400">{{ labels.empty }}</p>
		</div>

		<ul v-else class="oak-card divide-y divide-gray-100 overflow-hidden">
			<li v-for="r in items" :key="r.name" class="flex items-start gap-3 px-4 py-3">
				<span class="oak-icon-tile mt-0.5 h-9 w-9 bg-gray-100 text-gray-500"><Icon name="clipboard" :size="16" /></span>
				<div class="min-w-0 flex-1">
					<div class="flex items-center justify-between gap-2">
						<p class="truncate font-semibold text-gray-900">{{ r.container_no || r.container }}</p>
						<span class="oak-chip shrink-0" :class="statusClass(r)">{{ statusText(r) }}</span>
					</div>
					<div class="mt-0.5 flex items-center justify-between gap-2 text-xs text-gray-500">
						<span class="truncate">{{ r.inspection_type }}<span v-if="r.tank_status"> · {{ r.tank_status }}</span></span>
						<span class="shrink-0">{{ fmtDate(r.eir_date || r.creation) }}</span>
					</div>
					<p class="truncate text-[11px] text-gray-400">{{ r.inspection_id || r.name }}</p>
				</div>
			</li>
		</ul>

		<div v-if="total > 0" class="space-y-1.5">
			<div class="flex flex-wrap items-center justify-center gap-1.5">
				<button
					class="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-40"
					:disabled="page <= 1 || history.loading"
					@click="goTo(page - 1)"
				>
					<Icon name="chevron-left" :size="16" /> {{ labels.prev }}
				</button>
				<button
					v-for="p in pageWindow"
					:key="p"
					class="min-w-[2.5rem] rounded-lg border px-3 py-1.5 text-sm font-semibold transition"
					:class="p === page ? 'border-brand-600 bg-brand-600 text-white shadow-sm' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'"
					:disabled="history.loading"
					@click="goTo(p)"
				>
					{{ p }}
				</button>
				<button
					class="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-40"
					:disabled="page >= totalPages || history.loading"
					@click="goTo(page + 1)"
				>
					{{ labels.next }} <Icon name="chevron-right" :size="16" />
				</button>
			</div>
			<p class="text-center text-xs text-gray-400">{{ page }} / {{ totalPages }} · {{ total }} EIR</p>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue"
import { createResource } from "frappe-ui"
import { labels } from "@/utils/labels"
import Icon from "@/components/Icon.vue"

const PAGE = 10
const search = ref("")
const page = ref(1)
const items = ref([])
const total = ref(0)

// frappe-ui serializes GET params via URLSearchParams, turning `undefined` into the
// string "undefined" — only include keys that actually have a value.
function cleanParams(obj) {
	const out = {}
	for (const k in obj) {
		const v = obj[k]
		if (v !== undefined && v !== null && v !== "") out[k] = v
	}
	return out
}

const history = createResource({
	url: "container_depot.ess.inspections.eir_history",
	method: "GET",
	makeParams: () => cleanParams({ search: search.value, start: (page.value - 1) * PAGE, page_length: PAGE }),
	auto: true,
	onSuccess(data) {
		items.value = data.items || []
		total.value = data.total || 0
	},
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE)))

// A window of up to 5 page numbers centred on the current page.
const pageWindow = computed(() => {
	const tp = totalPages.value
	const max = 5
	let startP = Math.max(1, page.value - Math.floor(max / 2))
	const endP = Math.min(tp, startP + max - 1)
	startP = Math.max(1, endP - max + 1)
	const out = []
	for (let p = startP; p <= endP; p++) out.push(p)
	return out
})

function goTo(p) {
	page.value = Math.min(Math.max(1, p), totalPages.value)
	history.reload()
}

let searchTimer = null
function onSearchInput() {
	clearTimeout(searchTimer)
	searchTimer = setTimeout(() => {
		page.value = 1
		history.reload()
	}, 300)
}

function statusText(r) {
	if (r.docstatus === 1) return labels.eirStatusSubmitted
	if (r.docstatus === 2) return labels.eirStatusCancelled
	return labels.eirStatusDraft
}
function statusClass(r) {
	if (r.docstatus === 1) return "bg-leaf-100 text-leaf-800"
	if (r.docstatus === 2) return "bg-gray-200 text-gray-600"
	return "bg-amber-100 text-amber-800"
}
function fmtDate(v) {
	return v ? String(v).slice(0, 10) : "—"
}
</script>
