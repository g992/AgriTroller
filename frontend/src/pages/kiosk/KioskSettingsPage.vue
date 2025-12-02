<template>
  <q-page class="kiosk-page kiosk-settings">
    <q-card class="kiosk-card kiosk-network-card">
      <q-card-section class="row items-start justify-between q-gutter-sm">
        <div>
          <div class="text-h5 text-weight-bold">Сеть и доступ</div>
          <div class="text-caption text-grey-5">Экранная клавиатура открывается по нажатию на поле</div>
        </div>
        <q-btn
          flat
          dense
          round
          color="grey-5"
          :icon="networkSectionExpanded ? 'expand_less' : 'expand_more'"
          aria-label="Переключить раздел сети"
          @click="networkSectionExpanded = !networkSectionExpanded"
        />
      </q-card-section>
      <q-slide-transition>
        <div v-show="networkSectionExpanded">
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
        </div>
      </q-slide-transition>
    </q-card>
    <q-card class="kiosk-card kiosk-uart-card">
      <q-card-section class="row items-start justify-between q-gutter-sm">
        <div>
          <div class="text-h5 text-weight-bold">UART порты</div>
          <div class="text-caption text-grey-5">Периферия и RS-485 в киоск-режиме</div>
        </div>
        <div class="row items-center q-gutter-xs">
          <q-btn
            flat
            dense
            round
            color="secondary"
            icon="refresh"
            :loading="devicesLoading"
            :disable="devicesSaving"
            @click="refreshDevicesAndPorts"
          />
          <q-btn
            flat
            dense
            round
            color="grey-5"
            :icon="uartSectionExpanded ? 'expand_less' : 'expand_more'"
            aria-label="Переключить раздел UART"
            @click="uartSectionExpanded = !uartSectionExpanded"
          />
        </div>
      </q-card-section>
      <q-slide-transition>
        <div v-show="uartSectionExpanded">
          <q-separator dark />
          <q-card-section class="q-gutter-md">
            <q-banner v-if="devicesError" rounded dense class="bg-red-10 text-white q-mb-sm">
              {{ devicesError }}
            </q-banner>
            <div v-if="devicesLoading" class="row justify-center q-my-md">
              <q-spinner color="primary" size="32px" />
            </div>
            <div v-else class="column q-gutter-md">
              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <div class="text-subtitle2 text-white">Периферийные контроллеры</div>
                  <div class="text-caption text-grey-6">UART линии для периферии</div>
                  <div v-if="!peripheralDevices.length" class="text-grey-6 text-caption q-mt-sm">
                    Контроллеры ещё не добавлены.
                  </div>
                  <q-list
                    v-else
                    bordered
                    separator
                    class="rounded-borders kiosk-device-list"
                  >
                    <q-item v-for="device in peripheralDevices" :key="device.id">
                      <q-item-section avatar>
                        <q-icon name="memory" color="primary" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-white text-weight-medium">
                          {{ device.name }}
                        </q-item-label>
                        <q-item-label caption class="text-grey-5">
                          {{ device.port }} · {{ device.baudrate.toLocaleString('ru-RU') }} бод
                        </q-item-label>
                        <q-item-label caption class="text-grey-6">
                          Статус: {{ statusLabel(device.status) }} ·
                          {{ device.status_message || 'ещё не проверялся' }}
                        </q-item-label>
                        <q-item-label caption class="text-grey-7">
                          Проверено: {{ formatStatusTimestamp(device.status_checked_at) }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <div class="column items-end q-gutter-xs">
                          <q-chip
                            square
                            :color="statusColor(device.status)"
                            text-color="black"
                            size="sm"
                          >
                            {{ statusLabel(device.status) }}
                          </q-chip>
                          <q-chip
                            square
                            :color="device.enabled ? 'positive' : 'warning'"
                            text-color="black"
                            size="sm"
                          >
                            {{ device.enabled ? 'активен' : 'отключен' }}
                          </q-chip>
                        </div>
                      </q-item-section>
                      <q-item-section side top>
                        <div class="row items-center no-wrap q-gutter-xs">
                          <q-btn
                            dense
                            flat
                            round
                            icon="refresh"
                            color="accent"
                            :loading="isDeviceRefreshing(device.id)"
                            :disable="devicesSaving || isDeviceRefreshing(device.id)"
                            @click="refreshDeviceStatus(device.id)"
                          />
                          <q-btn
                            dense
                            flat
                            round
                            color="primary"
                            icon="edit"
                            :disable="devicesSaving"
                            @click="openEditDialog(device)"
                          />
                          <q-btn
                            dense
                            flat
                            round
                            color="negative"
                            icon="delete"
                            :disable="devicesSaving"
                            @click="requestDelete(device)"
                          />
                        </div>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
                <div class="col-12 col-md-6">
                  <div class="text-subtitle2 text-white">RS-485 шлюзы</div>
                  <div class="text-caption text-grey-6">Внешние шины и модбас</div>
                  <div v-if="!rs485Devices.length" class="text-grey-6 text-caption q-mt-sm">
                    Шлюзы ещё не добавлены.
                  </div>
                  <q-list
                    v-else
                    bordered
                    separator
                    class="rounded-borders kiosk-device-list"
                  >
                    <q-item v-for="device in rs485Devices" :key="device.id">
                      <q-item-section avatar>
                        <q-icon name="device_hub" color="secondary" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-white text-weight-medium">
                          {{ device.name }}
                        </q-item-label>
                        <q-item-label caption class="text-grey-5">
                          {{ device.port }} · {{ device.baudrate.toLocaleString('ru-RU') }} бод
                        </q-item-label>
                        <q-item-label caption class="text-grey-6">
                          Статус: {{ statusLabel(device.status) }} ·
                          {{ device.status_message || 'ещё не проверялся' }}
                        </q-item-label>
                        <q-item-label caption class="text-grey-7">
                          Проверено: {{ formatStatusTimestamp(device.status_checked_at) }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <div class="column items-end q-gutter-xs">
                          <q-chip
                            square
                            :color="statusColor(device.status)"
                            text-color="white"
                            size="sm"
                          >
                            {{ statusLabel(device.status) }}
                          </q-chip>
                          <q-chip
                            square
                            :color="device.enabled ? 'primary' : 'warning'"
                            text-color="white"
                            size="sm"
                          >
                            {{ device.enabled ? 'активен' : 'отключен' }}
                          </q-chip>
                        </div>
                      </q-item-section>
                      <q-item-section side top>
                        <div class="row items-center no-wrap q-gutter-xs">
                          <q-btn
                            dense
                            flat
                            round
                            icon="refresh"
                            color="accent"
                            :loading="isDeviceRefreshing(device.id)"
                            :disable="devicesSaving || isDeviceRefreshing(device.id)"
                            @click="refreshDeviceStatus(device.id)"
                          />
                          <q-btn
                            dense
                            flat
                            round
                            color="secondary"
                            icon="edit"
                            :disable="devicesSaving"
                            @click="openEditDialog(device)"
                          />
                          <q-btn
                            dense
                            flat
                            round
                            color="negative"
                            icon="delete"
                            :disable="devicesSaving"
                            @click="requestDelete(device)"
                          />
                        </div>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
              </div>

              <q-separator dark />

              <div>
                <div class="text-subtitle2 text-white q-mb-sm">Добавить UART порт</div>
                <q-banner v-if="portFormError" rounded dense class="bg-red-10 text-white q-mb-sm">
                  {{ portFormError }}
                </q-banner>
                <q-form @submit.prevent="submitPort" class="row q-col-gutter-md kiosk-port-form">
                  <div class="col-12 col-md-3">
                    <KioskKeyboardField
                      v-model="portForm.name"
                      label="Название"
                      hint="Например, UART контроллера"
                      :maxlength="64"
                      counter
                      :disable="devicesSaving"
                    />
                  </div>
                  <div class="col-12 col-md-3">
                    <q-select
                      v-model="portForm.kind"
                      :options="portTypeOptions"
                      emit-value
                      map-options
                      label="Тип порта"
                      standout="bg-dark"
                      stack-label
                      dense
                      :disable="devicesSaving"
                    />
                  </div>
                  <div class="col-12 col-md-3">
                    <KioskKeyboardField
                      v-model="portForm.port"
                      label="Системный путь"
                      hint="Укажите tty/COM или выберите из списка"
                      :suggestions="portOptions"
                      :disable="devicesSaving"
                    />
                  </div>
                  <div class="col-12 col-md-3">
                    <KioskKeyboardField
                      v-model="portForm.baudrate"
                      label="Скорость (бод)"
                      layout="numeric"
                      inputmode="numeric"
                      :disable="devicesSaving"
                    />
                  </div>
                  <div class="col-12 col-md-3">
                    <q-btn
                      type="submit"
                      color="primary"
                      label="Добавить"
                      class="full-width"
                      :loading="devicesSaving"
                      :disable="devicesSaving"
                    />
                  </div>
                </q-form>
              </div>
            </div>
          </q-card-section>
        </div>
      </q-slide-transition>
    </q-card>

    <q-dialog v-model="isEditDialogOpen">
      <q-card class="kiosk-card kiosk-edit-card">
        <q-card-section class="row items-start justify-between q-gutter-sm">
          <div>
            <div class="text-h6 text-white">Редактировать UART порт</div>
            <div class="text-caption text-grey-5">Обновите параметры подключения</div>
          </div>
          <q-btn dense flat round icon="close" color="grey-5" @click="closeEditDialog" />
        </q-card-section>
        <q-card-section class="q-gutter-md kiosk-dialog-body">
          <q-banner v-if="editFormError" rounded dense class="bg-red-10 text-white q-mb-sm">
            {{ editFormError }}
          </q-banner>
          <q-form @submit.prevent="submitEditForm" class="row q-col-gutter-md">
            <div class="col-12">
              <KioskKeyboardField
                v-model="editForm.name"
                label="Название"
                hint="Например, UART контроллера"
                :maxlength="64"
                counter
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12">
              <q-select
                v-model="editForm.kind"
                :options="portTypeOptions"
                emit-value
                map-options
                label="Тип порта"
                standout="bg-dark"
                stack-label
                dense
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12">
              <KioskKeyboardField
                v-model="editForm.port"
                label="Системный путь"
                hint="Укажите tty/COM или выберите из списка"
                :suggestions="portOptions"
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12">
              <KioskKeyboardField
                v-model="editForm.baudrate"
                label="Скорость (бод)"
                layout="numeric"
                inputmode="numeric"
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12">
              <q-toggle
                v-model="editForm.enabled"
                color="positive"
                label="Порт активен"
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12 q-gutter-sm text-right">
              <q-btn
                flat
                label="Отмена"
                color="white"
                :disable="devicesSaving"
                @click="closeEditDialog"
              />
              <q-btn
                type="submit"
                color="primary"
                label="Сохранить"
                :loading="devicesSaving"
                :disable="devicesSaving"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="isDeleteDialogOpen">
      <q-card class="kiosk-card kiosk-delete-card">
        <q-card-section class="row items-start q-gutter-sm">
          <q-icon name="warning" color="warning" size="32px" />
          <div>
            <div class="text-h6 text-white">Удалить порт?</div>
            <div class="text-grey-5">
              Это действие необратимо. Порт
              <strong>{{ deleteTarget ? deleteTarget.name : 'без названия' }}</strong>
              будет удалён из реестра.
            </div>
          </div>
        </q-card-section>
        <q-card-section v-if="deleteError">
          <q-banner dense rounded class="bg-red-10 text-white">
            {{ deleteError }}
          </q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            flat
            label="Отмена"
            color="white"
            :disable="devicesSaving"
            @click="closeDeleteDialog"
          />
          <q-btn
            color="negative"
            label="Удалить"
            :loading="devicesSaving"
            :disable="devicesSaving"
            @click="confirmDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

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
import { reactive, computed, onMounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useQuasar } from 'quasar';
import KioskKeyboard from 'components/KioskKeyboard.vue';
import KioskKeyboardField from 'components/KioskKeyboardField.vue';
import { useDeviceStore, type DeviceKind, type DeviceRecord, type DeviceUpdatePayload } from 'stores/device-store';
import { useWifiStore } from 'stores/wifi-store';

const $q = useQuasar();
const wifiStore = useWifiStore();
const { loading: wifiLoading, error: wifiError, networks } = storeToRefs(wifiStore);
const deviceStore = useDeviceStore();
const {
  peripheralDevices,
  rs485Devices,
  loading: devicesLoading,
  saving: devicesSaving,
  error: devicesError,
  portSuggestions,
} = storeToRefs(deviceStore);

const portTypeOptions = [
  { label: 'Периферийный контроллер', value: 'peripheral' as DeviceKind },
  { label: 'RS-485 шлюз', value: 'rs485' as DeviceKind },
];

const portForm = reactive<{ name: string; kind: DeviceKind; port: string; baudrate: string }>({
  name: '',
  kind: 'peripheral',
  port: '',
  baudrate: '115200',
});
const portFormError = ref<string | null>(null);

const editForm = reactive<{
  id: number | null;
  name: string;
  kind: DeviceKind;
  port: string;
  baudrate: string;
  enabled: boolean;
  mapping: Record<string, unknown> | null;
}>({
  id: null,
  name: '',
  kind: 'peripheral',
  port: '',
  baudrate: '115200',
  enabled: true,
  mapping: null,
});
const editFormError = ref<string | null>(null);
const isEditDialogOpen = ref(false);
const isDeleteDialogOpen = ref(false);
const deleteTarget = ref<DeviceRecord | null>(null);
const deleteError = ref<string | null>(null);
const refreshingDevices = ref<Set<number>>(new Set());
const portOptions = computed(() => {
  const options = (portSuggestions.value || []).filter((item) => !!item);
  return Array.from(new Set(options));
});

const uartSectionExpanded = ref(true);

const wifiForm = reactive({ ssid: '' });
const passwordInput = ref('');
const passwordDialog = ref(false);
const selectedNetwork = ref<string | null>(null);
const showPassword = ref(false);
const networkSectionExpanded = ref(true);

onMounted(() => {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    wifiForm.ssid = window.sessionStorage.getItem('kiosk-wifi-ssid') ?? '';
  }
  void wifiStore.fetchStatus();
  void wifiStore.fetchNetworks();
  void refreshDevicesAndPorts();
});

watch(uartSectionExpanded, (expanded) => {
  if (expanded) {
    void refreshDevicesAndPorts();
  }
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

function resetPortForm() {
  portForm.name = '';
  portForm.kind = 'peripheral';
  portForm.port = '';
  portForm.baudrate = '115200';
  portFormError.value = null;
}

function resetEditForm() {
  editForm.id = null;
  editForm.name = '';
  editForm.kind = 'peripheral';
  editForm.port = '';
  editForm.baudrate = '115200';
  editForm.enabled = true;
  editForm.mapping = null;
  editFormError.value = null;
}

async function refreshDevices() {
  await deviceStore.fetchDevices();
}

async function refreshDevicesAndPorts() {
  await Promise.all([deviceStore.fetchDevices(), deviceStore.fetchPortSuggestions()]);
}

async function submitPort() {
  portFormError.value = null;
  if (!portForm.name.trim() || !portForm.port.trim()) {
    portFormError.value = 'Укажите название и путь к порту';
    return;
  }
  try {
    await deviceStore.createDevice({
      kind: portForm.kind,
      name: portForm.name.trim(),
      port: portForm.port.trim(),
      baudrate: Math.max(300, Number(portForm.baudrate) || 0),
    });
    resetPortForm();
    void deviceStore.fetchPortSuggestions();
    $q.notify({ message: 'Порт добавлен', color: 'positive', textColor: 'black' });
  } catch {
    portFormError.value = devicesError.value ?? 'Не удалось сохранить порт';
  }
}

function openEditDialog(device: DeviceRecord) {
  editForm.id = device.id;
  editForm.name = device.name;
  editForm.kind = device.kind;
  editForm.port = device.port;
  editForm.baudrate = String(device.baudrate ?? '');
  editForm.enabled = device.enabled;
  editForm.mapping = device.mapping || null;
  editFormError.value = null;
  isEditDialogOpen.value = true;
}

function closeEditDialog() {
  isEditDialogOpen.value = false;
  resetEditForm();
}

async function submitEditForm() {
  editFormError.value = null;
  if (!editForm.id) {
    editFormError.value = 'Не выбран порт для редактирования';
    return;
  }
  if (!editForm.name.trim() || !editForm.port.trim()) {
    editFormError.value = 'Заполните название и путь к порту';
    return;
  }
  try {
    const payload: DeviceUpdatePayload = {
      name: editForm.name.trim(),
      kind: editForm.kind,
      port: editForm.port.trim(),
      baudrate: Math.max(300, Number(editForm.baudrate) || 0),
      enabled: editForm.enabled,
    };
    if (editForm.mapping) {
      payload.mapping = editForm.mapping;
    }
    await deviceStore.updateDevice(editForm.id, payload);
    closeEditDialog();
    $q.notify({ message: 'Изменения сохранены', color: 'positive', textColor: 'black' });
  } catch {
    editFormError.value = devicesError.value ?? 'Не удалось сохранить изменения';
  }
}

function requestDelete(device: DeviceRecord) {
  deleteTarget.value = device;
  deleteError.value = null;
  isDeleteDialogOpen.value = true;
}

function closeDeleteDialog() {
  deleteTarget.value = null;
  deleteError.value = null;
  isDeleteDialogOpen.value = false;
}

async function confirmDelete() {
  if (!deleteTarget.value) {
    return;
  }
  deleteError.value = null;
  try {
    await deviceStore.deleteDevice(deleteTarget.value.id);
    closeDeleteDialog();
    $q.notify({ message: 'Порт удалён', color: 'positive', textColor: 'black' });
  } catch {
    deleteError.value = devicesError.value ?? 'Не удалось удалить порт';
  }
}

function setRefreshing(deviceId: number, value: boolean) {
  const clone = new Set(refreshingDevices.value);
  if (value) {
    clone.add(deviceId);
  } else {
    clone.delete(deviceId);
  }
  refreshingDevices.value = clone;
}

function isDeviceRefreshing(deviceId: number) {
  return refreshingDevices.value.has(deviceId);
}

async function refreshDeviceStatus(deviceId: number) {
  if (isDeviceRefreshing(deviceId)) {
    return;
  }
  setRefreshing(deviceId, true);
  try {
    await deviceStore.refreshDeviceStatus(deviceId);
    await deviceStore.fetchPortSuggestions();
  } catch {
    // ошибка будет показана в баннере
  } finally {
    setRefreshing(deviceId, false);
  }
}

function statusColor(status?: string) {
  switch (status) {
    case 'available':
      return 'positive';
    case 'busy':
      return 'warning';
    case 'missing':
      return 'negative';
    default:
      return 'grey-7';
  }
}

function statusLabel(status?: string) {
  switch (status) {
    case 'available':
      return 'Доступен';
    case 'busy':
      return 'Занят';
    case 'missing':
      return 'Отсутствует';
    default:
      return 'Неизвестно';
  }
}

function formatStatusTimestamp(value?: string | null) {
  if (!value) {
    return 'не проверялось';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
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

.kiosk-network-card {
  margin-top: 16px;
}

.kiosk-uart-card {
  margin-top: 12px;
}

.kiosk-network-list {
  max-height: 480px;
  overflow-y: auto;
}

.kiosk-device-list {
  max-height: 360px;
  overflow-y: auto;
}

.kiosk-port-form .q-field {
  width: 100%;
}

.kiosk-edit-card,
.kiosk-delete-card {
  width: 100%;
  max-width: 760px;
}

.kiosk-dialog-body {
  padding-left: 18px;
  padding-right: 18px;
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
