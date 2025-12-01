<template>
  <q-layout view="hHh lpR fFf" class="kiosk-layout">
    <q-header elevated class="kiosk-header bg-dark text-white">
      <div class="header-bar">
        <div class="logo-wrapper">
          <q-img
            :src="logoUrl"
            alt="AgriTroller"
            class="logo-image"
            fit="contain"
            :img-style="{ objectFit: 'contain' }"
          />
        </div>
        <div class="row items-center q-gutter-sm header-actions">
          <div class="connection-indicator row items-center q-gutter-xs">
            <q-icon name="fiber_manual_record" :color="connectionColor" size="18px">
              <q-tooltip anchor="bottom middle" self="top middle" class="bg-grey-9 text-white">
                {{ connectionLabel }}
              </q-tooltip>
            </q-icon>
          </div>
          <div class="connection-indicator row items-center q-gutter-xs">
            <q-icon :name="wifiIcon" :color="wifiColor" size="20px">
              <q-tooltip anchor="bottom middle" self="top middle" class="bg-grey-9 text-white">
                {{ wifiTooltip }}
              </q-tooltip>
            </q-icon>
          </div>
          <q-btn
            unelevated
            no-caps
            color="grey-8"
            text-color="white"
            class="nav-btn"
            icon="desktop_windows"
            @click="go('/')"
          />
          <q-btn
            unelevated
            no-caps
            :color="isActive('/kiosk') ? 'primary' : 'grey-8'"
            text-color="white"
            class="nav-btn"
            icon="home"
            @click="go('/kiosk')"
          />
          <q-btn
            unelevated
            no-caps
            :color="isActive('/kiosk/settings') ? 'secondary' : 'grey-8'"
            text-color="white"
            class="nav-btn"
            icon="tune"
            @click="go('/kiosk/settings')"
          />
          <q-btn round dense color="grey-8" text-color="white" size="lg" icon="notifications" @click="openNotifications">
            <q-badge v-if="unreadCount" floating color="negative" transparent>{{ unreadCount }}</q-badge>
          </q-btn>
        </div>
      </div>
    </q-header>

    <q-page-container class="kiosk-container">
      <router-view />
    </q-page-container>

    <q-dialog
      v-model="notificationsOpen"
      maximized
      transition-show="fade"
      transition-hide="fade"
      class="kiosk-notifications-dialog"
      content-class="kiosk-dialog-inner"
      @show="refreshNotifications"
    >
      <q-card class="kiosk-notifications-card bg-dark text-white">
        <q-card-section class="row items-center justify-between q-pb-none">
          <div>
            <div class="text-h5 text-weight-bold">Уведомления</div>
            <div class="text-caption text-grey-5">Полноэкранный режим для быстрой реакции</div>
          </div>
          <div class="row items-center q-gutter-sm">
            <q-btn
              flat
              dense
              icon="done_all"
              label="прочитать"
              :disable="!unreadCount || notificationsSaving"
              @click="markAllNotificationsRead"
            />
            <q-btn
              flat
              dense
              color="negative"
              icon="delete_sweep"
              label="очистить"
              :disable="!notifications.length || notificationsSaving"
              @click="clearNotifications"
            />
            <q-btn flat dense round icon="close" color="grey-4" @click="closeNotifications" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-sm">
          <q-banner v-if="notificationsError" dense rounded class="bg-red-10 text-white q-mb-sm">
            {{ notificationsError }}
          </q-banner>
          <div v-if="notificationsLoading" class="flex flex-center q-pa-lg">
            <q-spinner color="primary" size="48px" />
          </div>
          <div v-else class="notification-scroll">
            <q-list separator dark>
              <q-item
                v-for="notification in notifications"
                :key="notification.id"
                clickable
                v-ripple
                :class="['notification-row', { 'notification-unread': !notification.is_read }]"
                @click="handleNotificationClick(notification)"
              >
                <q-item-section avatar>
                  <q-icon
                    :name="severityIcon(notification.severity)"
                    :color="severityColor(notification.severity)"
                    size="28px"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-subtitle1 text-white text-weight-medium">
                    {{ notification.message }}
                  </q-item-label>
                  <q-item-label caption class="text-grey-5">
                    {{ formatNotificationTime(notification.created_at) }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side top>
                  <q-badge :color="severityColor(notification.severity)" outline>
                    {{ severityLabel(notification.severity) }}
                  </q-badge>
                </q-item-section>
              </q-item>
              <div v-if="!notifications.length" class="text-grey-5 text-center q-pa-md">
                Нет уведомлений
              </div>
            </q-list>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useRoute, useRouter } from 'vue-router';
import { useEventStore } from 'stores/event-store';
import {
  useNotificationStore,
  type NotificationRecord,
  type NotificationSeverity,
} from 'stores/notification-store';
import { useWifiStore } from 'stores/wifi-store';
import logoUrl from 'assets/agritroller-logo.png';

const OPEN_NOTIFICATIONS_EVENT = 'kiosk-open-notifications';

const router = useRouter();
const route = useRoute();
const eventStore = useEventStore();
const notificationStore = useNotificationStore();
const wifiStore = useWifiStore();
const {
  notifications,
  unreadCount,
  loading: notificationsLoading,
  error: notificationsError,
  saving: notificationsSaving,
} = storeToRefs(notificationStore);
const { connectionState } = storeToRefs(eventStore);
const { status: wifiStatus, loading: wifiLoading } = storeToRefs(wifiStore);

const notificationsOpen = ref(false);

onMounted(() => {
  eventStore.connect();
  void notificationStore.fetchNotifications({ limit: 50 });
  void wifiStore.fetchStatus();
  if (typeof window !== 'undefined') {
    window.addEventListener(OPEN_NOTIFICATIONS_EVENT, openNotifications);
  }
});

onBeforeUnmount(() => {
  eventStore.disconnect();
  if (typeof window !== 'undefined') {
    window.removeEventListener(OPEN_NOTIFICATIONS_EVENT, openNotifications);
  }
});

function go(path: string) {
  if (route.path !== path) {
    void router.push(path);
  }
}

function isActive(path: string) {
  return route.path === path;
}

function openNotifications() {
  notificationsOpen.value = true;
}

function closeNotifications() {
  notificationsOpen.value = false;
}

function refreshNotifications() {
  void notificationStore.fetchNotifications({ limit: 50 });
}

async function handleNotificationClick(notification: NotificationRecord) {
  if (!notification.is_read) {
    try {
      await notificationStore.markAsRead(notification.id);
    } catch {
      // ошибка будет показана в баннере
    }
  }
}

async function markAllNotificationsRead() {
  try {
    await notificationStore.markAllRead();
  } catch {
    // handled via store
  }
}

async function clearNotifications() {
  if (!notifications.value.length) {
    return;
  }
  try {
    await notificationStore.deleteAll();
  } catch {
    // handled via store
  }
}

function severityColor(severity: NotificationSeverity) {
  switch (severity) {
    case 'error':
      return 'red-5';
    case 'warning':
      return 'amber-6';
    default:
      return 'positive';
  }
}

function severityIcon(severity: NotificationSeverity) {
  switch (severity) {
    case 'error':
      return 'warning';
    case 'warning':
      return 'priority_high';
    default:
      return 'check_circle';
  }
}

function severityLabel(severity: NotificationSeverity) {
  switch (severity) {
    case 'error':
      return 'Ошибка';
    case 'warning':
      return 'Предупреждение';
    default:
      return 'Ок';
  }
}

function formatNotificationTime(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

const connectionColor = computed(() => {
  switch (connectionState.value) {
    case 'connected':
      return 'positive';
    case 'reconnecting':
      return 'amber-7';
    default:
      return 'negative';
  }
});

const connectionLabel = computed(() => {
  switch (connectionState.value) {
    case 'connected':
      return 'Подключено';
    case 'reconnecting':
      return 'Переподключение';
    default:
      return 'Нет связи';
  }
});

const wifiIcon = computed(() => {
  if (wifiLoading.value) {
    return 'sync';
  }
  const status = wifiStatus.value?.status;
  if (status === 'connected') {
    return 'wifi_tethering';
  }
  if (status === 'connecting') {
    return 'sync';
  }
  return 'wifi_off';
});

const wifiColor = computed(() => {
  if (wifiLoading.value) {
    return 'grey-5';
  }
  const status = wifiStatus.value?.status;
  if (status === 'connected') {
    return 'positive';
  }
  if (status === 'connecting') {
    return 'amber-7';
  }
  return 'negative';
});

const wifiTooltip = computed(() => {
  if (wifiLoading.value) {
    return 'Обновляем состояние Wi‑Fi';
  }
  const status = wifiStatus.value;
  return (
    status?.message ||
    status?.last_error ||
    (status?.status === 'connected'
      ? 'Wi‑Fi подключено'
      : status?.status === 'connecting'
        ? 'Wi‑Fi подключение...'
        : 'Wi‑Fi не подключено')
  );
});

</script>

<style scoped lang="scss">
.kiosk-layout {
  background: radial-gradient(circle at 20% 20%, rgba(34, 197, 235, 0.08), transparent 45%),
    #020617;
  min-height: 100vh;
}

.kiosk-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  height: 70px;
  padding: 0 6px 0 2px;
}

.logo-image {
  height: 80px;
  width: auto !important;
  scale: 2.5;
  max-height: 70px;
  min-width: 160px;
  object-fit: contain;
}

.header-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.nav-btn {
  min-width: 52px;
  min-height: 52px;
  font-size: 16px;
  border-radius: 14px;
}

.connection-indicator {
  padding: 8px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
}

.kiosk-container {
  padding: 12px;
}

.kiosk-notifications-dialog {
  backdrop-filter: blur(4px);
}

.kiosk-notifications-card {
  width: 100%;
  max-width: 960px;
  margin: 0 auto;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(165deg, rgba(15, 23, 42, 0.98), rgba(6, 12, 24, 0.95));
  height: 100vh;
  max-height: none;
}

.notification-scroll {
  max-height: calc(100vh - 160px);
  overflow-y: auto;
}

.notification-row {
  padding: 16px 12px;
}

.notification-unread {
  background: rgba(14, 165, 233, 0.12);
}

@media (max-width: 700px) {
  .header-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .nav-btn {
    flex: 1;
  }
}

.kiosk-dialog-inner {
  padding: 0;
  height: 100vh;
}
</style>
