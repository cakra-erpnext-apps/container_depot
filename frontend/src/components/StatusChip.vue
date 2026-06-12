<template>
	<span
		class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
		:class="statusColors[bucket] || 'bg-gray-100 text-gray-700'"
	>
		{{ statusLabel(bucket) }}
	</span>
</template>

<script setup>
import { statusColors, statusLabel } from "@/utils/labels"

defineProps({
	bucket: { type: String, default: "" },
})
</script>
