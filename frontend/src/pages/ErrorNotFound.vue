<template>
  <div class="fullscreen error-page text-white text-center q-pa-md flex flex-center">
    <div>
      <div class="text-h1 text-weight-bolder">404</div>

      <div class="text-h4 text-grey-5 q-mt-md">Страница не найдена</div>

      <q-btn
        class="q-mt-xl"
        color="primary"
        icon="arrow_back"
        unelevated
        to="/"
        label="Вернуться на дашборд"
        no-caps
      />
    </div>
  </div>
</template>

<script setup lang="ts">
//
</script>

<style scoped lang="scss">
.error-page {
  background: radial-gradient(circle at center, rgba(14, 165, 233, 0.15), transparent 55%),
    #020617;
}
</style>
