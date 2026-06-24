<template>
	<HistoryPage
		:title="labels.mrHistoryTitle"
		icon="tool"
		back-to="/mr"
		:back-label="labels.mrTitleFull"
		list-url="container_depot.ess.repairs.mr_history"
		detail-url="container_depot.ess.repairs.mr_order_detail"
		detail-param="repair_order"
		:search-placeholder="labels.mrHistorySearch"
		:count-label="labels.mrHistoryCount"
	>
		<template #row="{ item }">
			<span class="oak-icon-tile h-9 w-9 shrink-0 bg-leaf-50 text-leaf-600"><Icon name="tool" :size="16" /></span>
			<div class="min-w-0 flex-1">
				<div class="flex items-center justify-between gap-2">
					<p class="truncate font-semibold text-gray-900">{{ item.container_no || item.container }}</p>
					<span class="oak-chip shrink-0" :class="statusClass(item.status)">{{ statusText(item.status) }}</span>
				</div>
				<div class="mt-0.5 flex items-center justify-between gap-2 text-xs text-gray-500">
					<span class="truncate">{{ item.repair_order_id }}</span>
					<span class="shrink-0">{{ fmtDate(item.completion_date || item.creation) }}</span>
				</div>
				<p v-if="item.principal" class="truncate text-[11px] text-gray-400">{{ item.principal }}</p>
			</div>
		</template>

		<template #detail="{ data }">
			<section class="oak-card space-y-3 p-4">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="font-mono text-xs text-gray-400">{{ data.repair_order_id }}</p>
						<h2 class="truncate text-lg font-extrabold text-gray-900">{{ data.container_no }}</h2>
					</div>
					<span class="oak-chip shrink-0" :class="statusClass(data.status)">{{ statusText(data.status) }}</span>
				</div>
				<dl class="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
					<div v-for="c in cells(data)" :key="c.label" class="min-w-0">
						<dt class="text-xs text-gray-400">{{ c.label }}</dt>
						<dd class="truncate font-medium text-gray-800">{{ c.value || "—" }}</dd>
					</div>
				</dl>
				<p v-if="data.owner_note" class="rounded-lg bg-amber-50 p-2 text-xs text-amber-700">
					<Icon name="message-square" :size="12" /> {{ data.owner_note }}
				</p>
			</section>

			<section v-if="(data.damages || []).length" class="oak-card space-y-2 p-4">
				<p class="oak-section-title">{{ labels.mrDamages }}</p>
				<ul class="space-y-1.5 text-sm">
					<li v-for="(d, i) in data.damages" :key="i" class="flex items-start gap-2 text-gray-800">
						<Icon name="alert-triangle" :size="14" class="mt-0.5 shrink-0 text-amber-500" />
						<span class="min-w-0">
							<span class="font-medium">{{ d.area || d.component || "—" }}</span>
							<span v-if="d.damage_desc" class="text-gray-500"> · {{ d.damage_desc }}</span>
							<span v-if="d.damage_description" class="block text-xs text-gray-400">{{ d.damage_description }}</span>
						</span>
					</li>
				</ul>
			</section>

			<section v-if="(data.used_items || []).length" class="oak-card space-y-2 p-4">
				<p class="oak-section-title">{{ labels.mrUsedItems }}</p>
				<ul class="space-y-1.5 text-sm">
					<li v-for="(u, i) in data.used_items" :key="i" class="flex items-center justify-between gap-2">
						<span class="min-w-0 flex-1 truncate text-gray-800">{{ u.item_name || u.item }}</span>
						<span class="shrink-0 text-xs text-gray-500">×{{ u.quantity }}</span>
						<span v-if="u.decision" class="oak-chip shrink-0" :class="decisionClass(u.decision)">{{ u.decision }}</span>
					</li>
				</ul>
			</section>
		</template>
	</HistoryPage>
</template>

<script setup>
import { labels, repairStatusLabels } from "@/utils/labels"
import Icon from "@/components/Icon.vue"
import HistoryPage from "@/components/HistoryPage.vue"

const fmtDate = (v) => (v ? String(v).slice(0, 10) : "—")

function statusText(s) {
	return repairStatusLabels[s] || s || "—"
}
function statusClass(s) {
	if (s === "Completed") return "bg-leaf-100 text-leaf-800"
	if (s === "Rejected") return "bg-red-100 text-red-700"
	if (s === "Cancelled") return "bg-gray-200 text-gray-600"
	return "bg-amber-100 text-amber-800"
}
function decisionClass(d) {
	if (d === "Approved") return "bg-leaf-100 text-leaf-800"
	if (d === "Rejected") return "bg-red-100 text-red-700"
	return "bg-gray-100 text-gray-500"
}
function cells(d) {
	return [
		{ label: labels.cleaningClient, value: d.client },
		{ label: labels.mrTechnician, value: d.technician },
		{ label: labels.cleaningRefEir, value: d.inspection },
		{ label: labels.cleaningTankType, value: d.tank_type },
	]
}
</script>
