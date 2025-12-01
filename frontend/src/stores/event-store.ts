import { defineStore } from 'pinia';
import { api } from 'boot/axios';
import {
  useNotificationStore,
  type NotificationSeverity,
} from './notification-store';
import { useWifiStore } from './wifi-store';

export interface EventEnvelope {
  type: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
  notify?: boolean;
  notification?: {
    severity: NotificationSeverity;
    message: string;
    source?: string;
    created_at?: string;
  };
}

export type ConnectionState = 'connected' | 'disconnected' | 'reconnecting';
const RECONNECT_INTERVAL_MS = 2000;

function resolveApiBase(): string {
  if (api.defaults.baseURL) {
    return api.defaults.baseURL.replace(/\/$/, '');
  }
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api`;
  }
  return 'http://localhost:8080/api';
}

function buildEventWsUrl(): string {
  const base = resolveApiBase();
  if (base.startsWith('https://')) {
    return `wss://${base.slice('https://'.length)}/ws/events`;
  }
  if (base.startsWith('http://')) {
    return `ws://${base.slice('http://'.length)}/ws/events`;
  }
  return `${base}/ws/events`;
}

export const useEventStore = defineStore('eventStream', {
  state: () => ({
    socket: null as WebSocket | null,
    isConnected: false,
    connectionState: 'disconnected' as ConnectionState,
    lastEvent: null as EventEnvelope | null,
    lastError: null as string | null,
    lastMessageAt: null as string | null,
    reconnectTimer: null as ReturnType<typeof setTimeout> | null,
    shouldReconnect: true,
  }),

  actions: {
    connect() {
      if (typeof window === 'undefined') {
        return;
      }
      this.shouldReconnect = true;
      this._openSocket();
    },

    _openSocket() {
      if (!this.shouldReconnect || this.socket) {
        return;
      }
      this.connectionState = 'reconnecting';
      const wsUrl = buildEventWsUrl();
      const socket = new WebSocket(wsUrl);
      this.socket = socket;

      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      socket.addEventListener('open', () => {
        this.isConnected = true;
        this.connectionState = 'connected';
        this.lastError = null;
      });

      socket.addEventListener('message', (message) => {
        try {
          this.lastEvent = JSON.parse(message.data) as EventEnvelope;
        this.lastMessageAt =
          this.lastEvent.timestamp ?? new Date().toISOString();
        this._handleEvent(this.lastEvent);
      } catch {
        this.lastError = 'Не удалось обработать событие шины';
        }
      });

      socket.addEventListener('close', () => {
        this.isConnected = false;
        this.connectionState = 'disconnected';
        this.socket = null;
        this._scheduleReconnect();
      });

      socket.addEventListener('error', () => {
        this.lastError = 'Ошибка подключения к шине событий';
        this.isConnected = false;
        this.connectionState = 'disconnected';
        this._scheduleReconnect();
      });
    },

    disconnect() {
      this.shouldReconnect = false;
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      this.isConnected = false;
      this.connectionState = 'disconnected';
    },

    _scheduleReconnect() {
      if (!this.shouldReconnect || this.reconnectTimer) {
        return;
      }
      this.connectionState = 'reconnecting';
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this._openSocket();
      }, RECONNECT_INTERVAL_MS);
    },

    _handleEvent(event: EventEnvelope) {
      if (event.notify && event.notification) {
        const notificationStore = useNotificationStore();
        notificationStore.pushTransient({
          severity: event.notification.severity,
          message: event.notification.message,
          source: event.notification.source ?? 'event_bus',
          event_type: event.type,
        });
      }

      if (event.type === 'wifi_status') {
        const wifiStore = useWifiStore();
        const notificationStore = useNotificationStore();
        const payload = (event.payload ?? {}) as {
          status?: string;
          ssid?: string;
          message?: string;
          last_error?: string | null;
        };
        const previousStatus = wifiStore.status?.status;
        wifiStore.applyStatusFromEvent(payload);

        if (payload.status && previousStatus !== payload.status) {
          if (payload.status === 'connected') {
            notificationStore.pushTransient({
              message: `Wi‑Fi подключен: ${payload.ssid || 'неизвестная сеть'}`,
              severity: 'ok',
              source: 'wifi',
              event_type: 'wifi_connected',
            });
          } else if (payload.status === 'disconnected') {
            notificationStore.pushTransient({
              message: payload.last_error
                ? `Wi‑Fi отключен: ${payload.last_error}`
                : 'Wi‑Fi отключен',
              severity: 'error',
              source: 'wifi',
              event_type: 'wifi_disconnected',
            });
          }
        }
      }
    },
  },
});
