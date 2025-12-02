<template>
  <q-page class="kiosk-page kiosk-settings">
    <q-card class="kiosk-card">
      <q-card-section>
        <div class="text-h5 text-weight-bold">Сеть и доступ</div>
        <div class="text-caption text-grey-5">Экранная клавиатура открывается по нажатию на поле</div>
      </q-card-section>
      <q-separator dark />
      <q-card-section class="q-gutter-md">
        <div class="row items-center justify-between q-mb-sm">
          <div class="text-subtitle2 text-white">Доступные сети</div>
          <q-btn
            flat
            dense
            color="secondary"
            icon="refresh"
            :loading="wifiLoading"
            @click="refreshNetworks"
          />
        </div>
        <q-banner v-if="wifiError" rounded dense class="bg-red-10 text-white q-mb-sm">
          {{ wifiError }}
        </q-banner>
        <div v-if="wifiLoading" class="row justify-center q-my-md">
          <q-spinner color="primary" size="32px" />
        </div>
        <q-list
          v-else
          bordered
          separator
          class="rounded-borders kiosk-network-list"
        >
          <q-item
            v-for="network in sortedNetworks"
            :key="network.ssid"
            clickable
            v-ripple
            :active="wifiForm.ssid === network.ssid"
            active-class="sidebar-active"
            @click="selectNetwork(network.ssid, network.security)"
          >
            <q-item-section avatar>
              <q-icon :name="network.active ? 'wifi_tethering' : 'wifi'" :color="network.active ? 'positive' : 'primary'" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-white text-weight-medium">
                {{ network.ssid || 'без имени' }}
              </q-item-label>
              <q-item-label caption class="text-grey-5">
                {{ network.security || 'open' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="text-caption text-grey-5 text-right">{{ network.signal }}%</div>
              <q-linear-progress
                :value="Math.min(1, Math.max(0, network.signal / 100))"
                color="primary"
                track-color="grey-9"
                size="8px"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!sortedNetworks.length">
            <q-item-section class="text-grey-6">
              Сети не найдены. Обновите список.
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
    <q-dialog
      v-model="passwordDialog"
      persistent
      :maximized="$q.screen.lt.lg"
      transition-show="slide-up"
      transition-hide="slide-down"
      class="kiosk-password-dialog"
    >
      <q-card class="kiosk-card kiosk-password-card">
        <q-card-section class="row items-start justify-between q-gutter-sm">
          <div>
            <div class="text-h6 text-white">Пароль для {{ selectedNetwork || 'сети' }}</div>
            <div class="text-caption text-grey-5">Введите пароль на экранной клавиатуре</div>
          </div>
          <q-btn dense flat round icon="close" color="grey-5" @click="closePasswordDialog" />
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="passwordInput"
            :type="showPassword ? 'text' : 'password'"
            label="Пароль"
            standout="bg-dark"
            dense
            rounded
            readonly
            stack-label
            :input-style="{ paddingTop: '18px', paddingBottom: '10px', fontSize: '18px' }"
          >
            <template #append>
              <q-icon
                :name="showPassword ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="showPassword = !showPassword"
              />
            </template>
          </q-input>
          <div class="q-mt-sm" />
          <KioskKeyboard
            v-model="passwordInput"
            layout="alphanumeric"
            title="Пароль Wi‑Fi"
            submit-label="Подключить"
            :show-close="false"
            :show-submit-button="false"
            @submit="submitPassword"
            @close="closePasswordDialog"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { reactive, computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useQuasar } from 'quasar';
import KioskKeyboard from 'components/KioskKeyboard.vue';
import { useWifiStore } from 'stores/wifi-store';

const $q = useQuasar();
const wifiStore = useWifiStore();
const { loading: wifiLoading, error: wifiError, networks } = storeToRefs(wifiStore);

const wifiForm = reactive({ ssid: '' });
const passwordInput = ref('');
const passwordDialog = ref(false);
const selectedNetwork = ref<string | null>(null);
const showPassword = ref(false);

onMounted(() => {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    wifiForm.ssid = window.sessionStorage.getItem('kiosk-wifi-ssid') ?? '';
  }
  void wifiStore.fetchStatus();
  void wifiStore.fetchNetworks();
});

const sortedNetworks = computed(() =>
  [...networks.value].sort((a, b) => Number(b.signal ?? 0) - Number(a.signal ?? 0)),
);

function selectNetwork(ssid: string, security?: string) {
  wifiForm.ssid = ssid;
  selectedNetwork.value = ssid;
  passwordInput.value = '';
  const isOpen = !security || security.toLowerCase().includes('open');
  if (isOpen) {
    void submitWifiWithPassword(ssid);
    return;
  }
  passwordDialog.value = true;
}


function refreshNetworks() {
  void wifiStore.fetchNetworks();
}

async function submitPassword() {
  if (!selectedNetwork.value) {
    passwordDialog.value = false;
    return;
  }
  await submitWifiWithPassword(selectedNetwork.value, passwordInput.value);
}

function closePasswordDialog() {
  passwordDialog.value = false;
  passwordInput.value = '';
  selectedNetwork.value = null;
}

async function submitWifiWithPassword(ssid: string, password?: string) {
  try {
    passwordDialog.value = false;
    showPassword.value = false;
    await wifiStore.connect({
      ssid,
      password: password || undefined,
    });
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.setItem('kiosk-wifi-ssid', ssid);
    }
    $q.notify({ message: 'Запрос на подключение отправлен', color: 'positive', textColor: 'black' });
    passwordInput.value = '';
    selectedNetwork.value = null;
    await Promise.all([wifiStore.fetchStatus(), wifiStore.fetchNetworks()]);
  } catch (error) {
    const message = wifiError.value || 'Не удалось подключить Wi‑Fi';
    $q.notify({ message, color: 'negative' });
    throw error;
  }
}
</script>

<style scoped lang="scss">
.kiosk-settings {
  gap: 12px;
}

.kiosk-card {
  background: #0b1221;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.kiosk-network-list {
  max-height: 480px;
  overflow-y: auto;
}

.kiosk-password-dialog :deep(.q-dialog__inner--maximized) {
  padding: 12px;
  align-items: flex-end;
}

.kiosk-password-card {
  width: 100%;
  max-width: 960px;
}

@media (max-width: 1024px) {
  .kiosk-password-card {
    max-width: none;
    border-radius: 14px 14px 0 0;
  }
}

@media (max-width: 720px) {
  .kiosk-password-dialog :deep(.q-dialog__inner--maximized) {
    padding: 0;
  }

  .kiosk-password-card {
    border-radius: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .kiosk-password-card .q-card__section:last-of-type {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .kiosk-password-card .kiosk-keyboard {
    flex: 1;
  }
}

@media (max-width: 640px) {
  .kiosk-card {
    border-radius: 14px;
  }
}
</style>
