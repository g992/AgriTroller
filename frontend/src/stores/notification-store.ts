import { defineStore } from 'pinia';
import { api } from 'boot/axios';

export type NotificationSeverity = 'ok' | 'warning' | 'error';

export interface NotificationRecord {
  id: number;
  event_type: string;
  severity: NotificationSeverity;
  source: string;
  message: string;
  created_at: string;
  is_read: boolean;
}

interface FetchParams {
  limit?: number;
  includeRead?: boolean;
}

function extractErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response: { data?: { detail?: string; message?: string } } }).response;
    const detail = response?.data?.detail ?? response?.data?.message;
    if (detail) {
      return detail;
    }
  }
  return 'Не удалось получить уведомления';
}

export const useNotificationStore = defineStore('notifications', {
  state: () => ({
    notifications: [] as NotificationRecord[],
    loading: false,
    saving: false,
    error: null as string | null,
  }),

  getters: {
    unreadCount: (state) => state.notifications.filter((n) => !n.is_read).length,
  },

  actions: {
    async fetchNotifications(params: FetchParams = {}) {
      this.loading = true;
      this.error = null;
      try {
        const response = await api.get<NotificationRecord[]>('/notifications', {
          params: {
            limit: params.limit ?? 20,
            include_read: params.includeRead ?? true,
          },
        });
        this.notifications = response.data;
      } catch (error) {
        this.error = extractErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },

    async markAsRead(notificationId: number) {
      const target = this.notifications.find((notification) => notification.id === notificationId);
      if (!target || target.is_read) {
        return;
      }
      this.saving = true;
      this.error = null;
      try {
        await api.post(`/notifications/${notificationId}/read`);
        target.is_read = true;
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async markAllRead() {
      const hasUnread = this.notifications.some((notification) => !notification.is_read);
      if (!hasUnread) {
        return;
      }
      this.saving = true;
      this.error = null;
      try {
        await api.post('/notifications/read-all');
        this.notifications = this.notifications.map((notification) => ({
          ...notification,
          is_read: true,
        }));
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async deleteNotification(notificationId: number) {
      this.saving = true;
      this.error = null;
      try {
        await api.delete(`/notifications/${notificationId}`);
        this.notifications = this.notifications.filter(
          (notification) => notification.id !== notificationId
        );
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async deleteAll() {
      if (!this.notifications.length) {
        return;
      }
      this.saving = true;
      this.error = null;
      try {
        await api.delete('/notifications');
        this.notifications = [];
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    pushTransient(payload: {
      message: string;
      severity?: NotificationSeverity;
      source?: string;
      event_type?: string;
    }) {
      const now = new Date().toISOString();
      const transient: NotificationRecord = {
        id: -Math.floor(Math.random() * 1_000_000),
        event_type: payload.event_type ?? 'transient',
        severity: payload.severity ?? 'ok',
        source: payload.source ?? 'wifi',
        message: payload.message,
        created_at: now,
        is_read: false,
      };
      this.notifications = [transient, ...this.notifications].slice(0, 50);
    },
  },
});
