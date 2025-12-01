<template>
  <q-page class="kiosk-page flex flex-center">
    <div class="empty-state text-center">
      <q-icon name="dashboard_customize" color="grey-6" size="64px" />
      <div class="text-h5 text-white text-weight-bold q-mt-md">Главная панель обновляется</div>
      <div class="text-subtitle2 text-grey-5 q-mt-xs">Плитки временно скрыты в киоск-режиме</div>
    </div>
  </q-page>
</template>

<style scoped lang="scss">
.kiosk-page {
  padding: 24px;
}

.empty-state {
  max-width: 520px;
  padding: 32px 28px;
  background: rgba(11, 18, 33, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 18px;
  box-shadow: 0 14px 38px rgba(0, 0, 0, 0.35);
}
</style>
