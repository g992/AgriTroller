import { defineStore } from 'pinia';
import { api } from 'boot/axios';

export interface WifiNetwork {
  ssid: string;
  signal: number;
  security: string;
  active?: boolean;
}

export interface WifiStatus {
  ssid?: string | null;
  status: string;
  last_connected_at?: string | null;
  last_error?: string | null;
  message?: string | null;
}

export interface WifiConnectPayload {
  ssid: string;
  password?: string | undefined;
}

function extractErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response: { data?: { detail?: string; message?: string } } }).response;
    const detail = response?.data?.detail ?? response?.data?.message;
    if (detail) {
      return detail;
    }
  }
  return 'Не удалось связаться с API AgriTroller';
}

export const useWifiStore = defineStore('wifi', {
  state: () => ({
    networks: [] as WifiNetwork[],
    status: null as WifiStatus | null,
    loading: false,
    connecting: false,
    error: null as string | null,
  }),

  actions: {
    async fetchNetworks() {
      this.loading = true;
      this.error = null;
      try {
        const response = await api.get<{ networks?: WifiNetwork[] }>('/wifi/networks');
        this.networks = Array.isArray(response.data?.networks)
          ? response.data.networks.map((network) => ({
              ...network,
              signal: Number(network.signal) || 0,
            }))
          : [];
      } catch (error) {
        this.error = extractErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },

    async fetchStatus() {
      this.error = null;
      try {
        const response = await api.get<WifiStatus>('/wifi/status');
        this.status = response.data;
      } catch (error) {
        this.error = extractErrorMessage(error);
      }
    },

    async connect(payload: WifiConnectPayload) {
      this.connecting = true;
      this.error = null;
      try {
        const response = await api.post<WifiStatus>('/wifi/connect', payload);
        this.status = response.data;
        return response.data;
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.connecting = false;
      }
    },

    applyStatusFromEvent(status: Partial<WifiStatus>) {
      const current = this.status ?? {
        ssid: null,
        status: 'disconnected',
        last_connected_at: null,
        last_error: null,
        message: null,
      };
      this.status = {
        ssid: status.ssid ?? current.ssid ?? null,
        status: status.status ?? current.status ?? 'disconnected',
        last_connected_at:
          status.last_connected_at ?? current.last_connected_at ?? null,
        last_error:
          status.last_error ?? current.last_error ?? null,
        message: status.message ?? current.message ?? null,
      };
      if (this.networks?.length && (status.ssid ?? current.ssid)) {
        const activeSsid = status.ssid ?? current.ssid;
        this.networks = this.networks.map((network) => ({
          ...network,
          active: network.ssid === activeSsid,
        }));
      }
    },
  },
});
