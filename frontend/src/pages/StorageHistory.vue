<template>
	<HistoryPage
		:title="labels.storageHistoryTitle"
		icon="layers"
		back-to="/storage"
		:back-label="labels.storage"
		list-url="container_depot.ess.yard.yard_history"
		detail-url="container_depot.ess.yard.movement_detail"
		detail-param="name"
		:search-placeholder="labels.storageHistorySearch"
		:count-label="labels.storageHistoryCount"
	>
		<template #row="{ item }">
			<span class="oak-icon-tile h-9 w-9 shrink-0 bg-leaf-50 text-leaf-600"><Icon name="layers" :size="16" /></span>
			<div class="min-w-0 flex-1">
				<div class="flex items-center justify-between gap-2">
					<p class="truncate font-semibold text-gray-900">{{ item.container }}</p>
					<span class="oak-chip shrink-0 bg-gray-100 text-gray-600">{{ eventText(item.event_type) }}</span>
				</div>
				<div class="mt-0.5 flex items-center justify-between gap-2 text-xs text-gray-500">
					<span class="truncate">{{ moveSummary(item) }}</span>
					<span class="shrink-0">{{ fmtDateTime(item.movement_timestamp) }}</span>
				</div>
			</div>
		</template>

		<template #detail="{ data }">
			<section class="oak-card space-y-3 p-4">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="text-xs text-gray-400">{{ fmtDateTime(data.movement_timestamp) }}</p>
						<h2 class="truncate text-lg font-extrabold text-gray-900">{{ data.container }}</h2>
					</div>
					<span class="oak-chip shrink-0 bg-gray-100 text-gray-600">{{ eventText(data.event_type) }}</span>
				</div>

				<div v-if="data.from_zone || data.to_zone" class="rounded-xl border border-gray-100 p-3">
					<p class="mb-1 text-xs font-bold uppercase tracking-wide text-gray-400">{{ labels.storageZoneMove }}</p>
					<p class="text-sm font-medium text-gray-800">
						{{ slot(data.from_zone, data.from_row, data.from_bay, data.from_tier) }}
						<Icon name="arrow-right" :size="14" class="mx-1 inline text-gray-400" />
						{{ slot(data.to_zone, data.to_row, data.to_bay, data.to_tier) }}
					</p>
				</div>

				<div v-if="data.from_status || data.to_status" class="rounded-xl border border-gray-100 p-3">
					<p class="mb-1 text-xs font-bold uppercase tracking-wide text-gray-400">{{ labels.storageStatusMove }}</p>
					<p class="text-sm font-medium text-gray-800">
						{{ data.from_status || "—" }}
						<Icon name="arrow-right" :size="14" class="mx-1 inline text-gray-400" />
						{{ data.to_status || "—" }}
					</p>
				</div>

				<dl class="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
					<div class="min-w-0">
						<dt class="text-xs text-gray-400">{{ labels.depotLabel }}</dt>
						<dd class="truncate font-medium text-gray-800">{{ data.depot || "—" }}</dd>
					</div>
					<div class="min-w-0">
						<dt class="text-xs text-gray-400">{{ labels.storageMovedBy }}</dt>
						<dd class="truncate font-medium text-gray-800">{{ data.moved_by || "—" }}</dd>
					</div>
				</dl>
			</section>
		</template>
	</HistoryPage>
</template>

<script setup>
import { labels } from "@/utils/labels"
import Icon from "@/components/Icon.vue"
import HistoryPage from "@/components/HistoryPage.vue"

const fmtDateTime = (v) => (v ? String(v).slice(0, 16).replace("T", " ") : "—")

function eventText(e) {
	return labels.storageEvent?.[e] || e || "—"
}
function slot(zone, row, bay, tier) {
	if (!zone) return "—"
	const pos = [row, bay, tier].filter((x) => x !== null && x !== undefined && x !== "").join("/")
	return pos ? `${zone} (${pos})` : zone
}
function moveSummary(m) {
	if (m.event_type === "Status" || (!m.from_zone && !m.to_zone)) {
		return `${m.from_status || "—"} → ${m.to_status || "—"}`
	}
	return `${m.from_zone || "—"} → ${m.to_zone || "—"}`
}
</script>
