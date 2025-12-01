<template>
  <q-card class="status-card q-pa-md column justify-between">
    <div class="row items-center q-col-gutter-xs">
      <q-icon :name="icon" size="32px" class="text-primary" />
      <div>
        <div class="text-caption text-grey-4">{{ label }}</div>
        <div class="text-h6 text-weight-bold text-white">{{ value }}</div>
      </div>
    </div>
    <slot />
  </q-card>
</template>

<script setup lang="ts">
interface Props {
  label: string;
  value: string | number;
  icon?: string;
}

withDefaults(defineProps<Props>(), {
  icon: 'analytics',
});
</script>

<style scoped lang="scss">
.status-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(8px);
  min-height: 140px;
}
</style>
