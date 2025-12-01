<template>
  <q-layout view="hHh lpR fFf" class="main-layout">
    <q-header elevated class="bg-dark text-white">
      <q-toolbar class="main-toolbar">
        <q-toolbar-title class="q-px-none">
          <div class="logo-wrapper">
            <q-img
              :src="logoUrl"
              alt="AgriTroller"
              class="logo-image"
              fit="contain"
              :img-style="{ objectFit: 'contain' }"
            />
          </div>
        </q-toolbar-title>
        <q-space />
        <div class="connection-indicator">
          <q-icon
            name="fiber_manual_record"
            :color="connectionColor"
            size="18px"
            class="cursor-pointer"
          >
            <q-tooltip
              anchor="bottom middle"
              self="top middle"
              class="bg-grey-9 text-white"
            >
              <div class="text-subtitle2 text-white">{{ connectionLabel }}</div>
              <div class="text-caption text-grey-4">
                Последнее сообщение: {{ lastMessageLabel }}
              </div>
            </q-tooltip>
          </q-icon>
        </div>
        <q-btn
          round
          dense
          flat
          icon="notifications"
          aria-label="Notifications"
          class="q-mr-sm"
        >
          <q-badge v-if="unreadCount" floating color="negative" transparent>{{ unreadCount }}</q-badge>
          <q-menu
            anchor="bottom right"
            self="top right"
            class="notifications-menu"
            @show="handleNotificationMenuShow"
          >
            <q-card class="notifications-card">
              <q-card-section class="row items-center justify-between">
                <div class="text-subtitle2 text-white">Уведомления</div>
                <div class="row items-center q-gutter-xs">
                  <q-btn
                    flat
                    dense
                    size="sm"
                    icon="done_all"
                    label="прочитать все"
                    :disable="!unreadCount || notificationsSaving"
                    @click.stop="markAllNotificationsRead"
                  />
                  <q-btn
                    flat
                    dense
                    size="sm"
                    color="negative"
                    icon="delete_sweep"
                    label="очистить"
                    :disable="!notifications.length || notificationsSaving"
                    @click.stop="confirmClearNotifications"
                  />
                </div>
              </q-card-section>
              <q-separator dark />
              <q-card-section v-if="notificationsError" class="bg-red-10 text-white">
                {{ notificationsError }}
              </q-card-section>
              <div v-if="notificationsLoading" class="q-pa-md flex flex-center">
                <q-spinner color="primary" size="32px" />
              </div>
              <q-list
                v-else-if="notifications.length"
                separator
                dark
                class="notifications-list"
              >
                <q-item
                  v-for="notification in notifications"
                  :key="notification.id"
                  clickable
                  v-ripple
                  :class="{ 'notification-unread': !notification.is_read }"
                  @click="handleNotificationClick(notification)"
                >
                  <q-item-section avatar>
                    <div class="row items-center no-wrap q-gutter-xs">
                      <q-icon
                        :name="severityIcon(notification.severity)"
                        :color="severityColor(notification.severity)"
                      />
                      <q-icon
                        :name="componentIcon(notification.source)"
                        :color="componentColor(notification.source)"
                        size="18px"
                        class="component-icon"
                      >
                        <q-tooltip
                          anchor="bottom middle"
                          self="top middle"
                          class="bg-grey-9 text-white"
                        >
                          {{ componentLabel(notification.source) }}
                        </q-tooltip>
                      </q-icon>
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-white text-weight-medium">
                      {{ notification.message }}
                    </q-item-label>
                    <q-item-label caption class="text-grey-5">
                      {{ componentLabel(notification.source) }} ·
                      {{ formatNotificationTime(notification.created_at) }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side top>
                    <div class="row items-center no-wrap q-gutter-xs">
                      <q-badge
                        outline
                        :color="severityColor(notification.severity)"
                        class="text-uppercase"
                      >
                        {{ severityLabel(notification.severity) }}
                      </q-badge>
                      <q-btn
                        flat
                        round
                        dense
                        size="sm"
                        color="grey-5"
                        icon="delete"
                        :disable="notificationsSaving"
                        @click.stop="removeNotification(notification.id)"
                      >
                        <q-tooltip class="bg-grey-9 text-white">
                          Удалить
                        </q-tooltip>
                      </q-btn>
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-else class="text-grey-5 q-pa-md text-center">
                Пока нет уведомлений
              </div>
            </q-card>
          </q-menu>
        </q-btn>
        <q-btn
          round
          dense
          flat
          icon="tablet_mac"
          aria-label="Kiosk"
          @click="goKiosk"
        >
          <q-tooltip class="bg-grey-9 text-white">Киоск режим</q-tooltip>
        </q-btn>
        <q-btn
          round
          dense
          flat
          icon="settings"
          aria-label="Settings"
          @click="goSettings"
        />
      </q-toolbar>
    </q-header>
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useQuasar } from 'quasar';
import { useEventStore } from 'stores/event-store';
import {
  useNotificationStore,
  type NotificationRecord,
  type NotificationSeverity,
} from 'stores/notification-store';
import logoUrl from 'assets/agritroller-logo.png';

const router = useRouter();
const eventStore = useEventStore();
const notificationStore = useNotificationStore();
const {
  notifications,
  loading: notificationsLoading,
  error: notificationsError,
  unreadCount,
  saving: notificationsSaving,
} = storeToRefs(notificationStore);
const { connectionState, lastMessageAt } = storeToRefs(eventStore);
const $q = useQuasar();

onMounted(() => {
  eventStore.connect();
  void notificationStore.fetchNotifications();
});

onBeforeUnmount(() => {
  eventStore.disconnect();
});

function handleNotificationMenuShow() {
  void notificationStore.fetchNotifications();
}

async function handleNotificationClick(notification: NotificationRecord) {
  try {
    await notificationStore.markAsRead(notification.id);
  } catch {
    // ignore errors here; banner will display inside the dropdown
  }
}

async function markAllNotificationsRead() {
  try {
    await notificationStore.markAllRead();
  } catch {
    // handled by store error
  }
}

async function removeNotification(notificationId: number) {
  try {
    await notificationStore.deleteNotification(notificationId);
  } catch {
    // handled by store error
  }
}

function confirmClearNotifications() {
  if (!notifications.value.length || notificationsSaving.value) {
    return;
  }
  $q.dialog({
    title: 'Очистить уведомления?',
    message: 'Все уведомления будут удалены без возможности восстановления.',
    cancel: { label: 'Отмена', color: 'grey-5' },
    ok: { label: 'Удалить', color: 'negative' },
    persistent: true,
    dark: true,
  }).onOk(() => {
    void (async () => {
      try {
        await notificationStore.deleteAll();
      } catch {
        // handled by store error
      }
    })();
  });
}

function goSettings() {
  void router.push('/settings');
}

function goKiosk() {
  void router.push('/kiosk');
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
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

interface ComponentMeta {
  icon: string;
  label: string;
  color: string;
}

const COMPONENTS: Record<string, ComponentMeta> = {
  port_monitor: {
    icon: 'usb',
    label: 'Монитор портов',
    color: 'cyan-4',
  },
  peripheral_service: {
    icon: 'developer_board',
    label: 'Контроллер периферии',
    color: 'teal-4',
  },
  scheduler: {
    icon: 'schedule',
    label: 'Планировщик',
    color: 'light-blue-4',
  },
  web: {
    icon: 'lan',
    label: 'Веб-сервер',
    color: 'deep-purple-3',
  },
};

function componentIcon(source: string) {
  return COMPONENTS[source]?.icon ?? 'widgets';
}

function componentLabel(source: string) {
  if (!source) {
    return 'Неизвестный компонент';
  }
  return COMPONENTS[source]?.label ?? source;
}

function componentColor(source: string) {
  return COMPONENTS[source]?.color ?? 'grey-5';
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
      return 'Нет подключения';
  }
});

const lastMessageLabel = computed(() => {
  if (!lastMessageAt.value) {
    return 'нет данных';
  }
  const parsed = new Date(lastMessageAt.value);
  return Number.isNaN(parsed.getTime()) ? lastMessageAt.value : parsed.toLocaleString();
});
</script>

<style scoped lang="scss">
.main-layout {
  background-color: #020617;
}

.main-toolbar {
  min-height: 72px;
  padding-left: 12px;
  padding-right: 12px;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  height: 80px;
  padding: 0 6px 0 2px;
}

.logo-image {
  height: 100px;
  width: auto !important;
  max-height: 96px;
  scale: 1.5;
  min-width: 200px;
  max-width: 360px;
  border-radius: 0;
  background: transparent;
  object-fit: contain;
  flex-shrink: 0;
}

.notifications-card {
  width: 360px;
  max-width: 90vw;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.notifications-list {
  max-height: 320px;
  overflow-y: auto;
}

.notification-unread {
  background-color: rgba(14, 165, 233, 0.08);
}

.component-icon {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  padding: 2px;
  background: rgba(255, 255, 255, 0.05);
}
</style>
