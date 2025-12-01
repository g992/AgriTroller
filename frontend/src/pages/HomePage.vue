<template>
  <q-page class="home-page column items-center justify-center q-pa-xl">
    <div class="text-h3 text-white text-center text-weight-bold q-mb-md">
      AgriTroller Console
    </div>
    <div class="text-subtitle1 text-grey-5 text-center q-mb-xl">
      Центр управления агро и гидропонными системами. Перейдите в настройки, чтобы
      управлять устройствами, портами и обновлениями.
    </div>
    <div class="row q-col-gutter-md">
      <div class="col-auto">
        <q-btn color="primary" icon="settings" label="Открыть настройки" to="/settings" />
      </div>
      <div class="col-auto">
        <q-btn color="secondary" outline icon="monitor" label="Открыть фронтенд" to="/app" />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
// landing component uses static content for now
</script>

<style scoped lang="scss">
.home-page {
  min-height: 100vh;
  background: radial-gradient(circle at top, rgba(34, 211, 238, 0.08), transparent 40%),
    #020617;
}
</style>
