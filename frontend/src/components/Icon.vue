<template>
	<!-- feather toSvg() emits stroke="currentColor", so colour follows `text-*`. -->
	<span class="inline-flex shrink-0 items-center justify-center" v-html="svg" />
</template>

<script setup>
import { computed } from "vue"
import feather from "feather-icons"

const props = defineProps({
	name: { type: String, required: true },
	size: { type: [Number, String], default: 20 },
	stroke: { type: [Number, String], default: 2 },
})

const svg = computed(() => {
	const icon = feather.icons[props.name]
	if (!icon) return ""
	return icon.toSvg({
		width: props.size,
		height: props.size,
		"stroke-width": props.stroke,
	})
})
</script>
