import { defineStore } from 'pinia';
import { api } from 'boot/axios';

export type DeviceKind = 'peripheral' | 'rs485';

export interface DeviceRecord {
  id: number;
  kind: DeviceKind;
  name: string;
  port: string;
  baudrate: number;
  metadata: Record<string, unknown>;
  device_type_slug?: string;
  mapping?: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  status?: string;
  status_message?: string | null;
  status_checked_at?: string | null;
}

export interface DevicePayload {
  kind: DeviceKind;
  name: string;
  port: string;
  baudrate: number;
  metadata?: Record<string, unknown>;
  device_type_slug?: string;
  mapping?: Record<string, unknown>;
  enabled?: boolean;
}

export interface DeviceUpdatePayload {
  kind?: DeviceKind;
  name?: string;
  port?: string;
  baudrate?: number;
  metadata?: Record<string, unknown>;
  device_type_slug?: string;
  mapping?: Record<string, unknown>;
  enabled?: boolean;
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

export const useDeviceStore = defineStore('devices', {
  state: () => ({
    devices: [] as DeviceRecord[],
    loading: false,
    saving: false,
    error: null as string | null,
    portSuggestions: [] as string[],
    loadingPorts: false,
  }),

  getters: {
    peripheralDevices: (state) => state.devices.filter((device) => device.kind === 'peripheral'),
    rs485Devices: (state) => state.devices.filter((device) => device.kind === 'rs485'),
  },

  actions: {
    async fetchDevices(kind?: DeviceKind) {
      this.loading = true;
      this.error = null;
      try {
        const response = await api.get<DeviceRecord[]>('/devices', {
          params: kind ? { kind } : undefined,
        });
        this.devices = response.data;
      } catch (error) {
        this.error = extractErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },

    async createDevice(payload: DevicePayload) {
      this.saving = true;
      this.error = null;
      try {
        await api.post('/devices', payload);
        await this.fetchDevices();
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async updateDevice(deviceId: number, payload: DeviceUpdatePayload) {
      this.saving = true;
      this.error = null;
      try {
        await api.put(`/devices/${deviceId}`, payload);
        await this.fetchDevices();
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async deleteDevice(deviceId: number) {
      this.saving = true;
      this.error = null;
      try {
        await api.delete(`/devices/${deviceId}`);
        await this.fetchDevices();
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async fetchPortSuggestions() {
      this.loadingPorts = true;
      try {
        const response = await api.get<{ ports?: string[] }>('/devices/ports');
        const incoming = Array.isArray(response.data?.ports) ? response.data?.ports ?? [] : [];
        this.portSuggestions = normalizePortList(incoming);
      } catch {
        this.portSuggestions = fallbackPortSuggestions();
      } finally {
        this.loadingPorts = false;
      }
    },

    async refreshDeviceStatus(deviceId: number) {
      this.error = null;
      try {
        const response = await api.post<DeviceRecord>(`/devices/${deviceId}/refresh-port`);
        this.devices = this.devices.map((device) =>
          device.id === deviceId ? response.data : device,
        );
      } catch (error) {
        this.error = extractErrorMessage(error);
        throw error;
      }
    },
  },
});

function normalizePortList(ports: string[]): string[] {
  const unique = Array.from(new Set(ports.filter((value) => typeof value === 'string' && value.trim())));
  return unique;
}

function fallbackPortSuggestions(): string[] {
  if (typeof navigator === 'undefined') {
    return ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', 'COM3', 'COM4'];
  }
  const platform = navigator.platform?.toLowerCase() ?? '';
  if (platform.includes('win')) {
    return ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6'];
  }
  if (platform.includes('mac') || platform.includes('darwin')) {
    return ['/dev/tty.usbserial-0001', '/dev/tty.usbmodem-0001', '/dev/cu.usbserial-0001'];
  }
  return ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyS0'];
}
