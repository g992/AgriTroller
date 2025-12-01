import { defineStore } from 'pinia';
import { api } from 'boot/axios';

export interface TemplateContent {
  devices?: unknown[];
  registers?: unknown[];
  [key: string]: unknown;
}

export interface TemplateRecord {
  id: number;
  slug: string;
  name: string;
  content: TemplateContent;
  updated_at: string;
}

export interface VersionBag {
  backend: string;
  frontend: string;
  firmware: string;
}

export interface SystemMetrics {
  cpu: {
    percent: number;
    load_average: number[] | null;
    cores: number;
  };
  memory: {
    total_bytes: number;
    used_bytes: number;
    available_bytes: number;
    percent: number;
  };
  storage: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    percent: number;
    mount: string;
  };
  database: {
    path: string | null;
    size_bytes: number;
  };
  collected_at: string;
}

interface ApiError {
  message: string;
}

export const useAppStore = defineStore('app', {
  state: () => ({
    templateList: [] as TemplateRecord[],
    versions: null as VersionBag | null,
    systemMetrics: null as SystemMetrics | null,
    loadingTemplates: false,
    loadingVersions: false,
    loadingSystem: false,
    lastError: null as string | null,
  }),

  actions: {
    async fetchTemplates() {
      this.loadingTemplates = true;
      try {
        const response = await api.get<TemplateRecord[]>('/templates');
        this.templateList = response.data;
      } catch (error) {
        this.lastError = this.extractErrorMessage(error);
      } finally {
        this.loadingTemplates = false;
      }
    },

    async fetchVersions() {
      this.loadingVersions = true;
      try {
        const response = await api.get<VersionBag>('/versions');
        this.versions = response.data;
      } catch (error) {
        this.lastError = this.extractErrorMessage(error);
      } finally {
        this.loadingVersions = false;
      }
    },

    async fetchSystemMetrics() {
      this.loadingSystem = true;
      try {
        const response = await api.get<SystemMetrics>('/system/metrics');
        this.systemMetrics = response.data;
      } catch (error) {
        this.lastError = this.extractErrorMessage(error);
      } finally {
        this.loadingSystem = false;
      }
    },

    async loadSettingsData() {
      this.lastError = null;
      await Promise.all([this.fetchVersions(), this.fetchTemplates(), this.fetchSystemMetrics()]);
    },

    extractErrorMessage(error: unknown): string {
      if (error && typeof error === 'object' && 'response' in error) {
        const response = (error as { response: { data?: ApiError } }).response;
        if (response?.data?.message) {
          return response.data.message;
        }
      }
      return 'Не удалось связаться с API AgriTroller';
    },
  },

  getters: {
    hasTemplates: (state) => state.templateList.length > 0,
  },
});
