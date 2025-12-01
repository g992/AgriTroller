import { defineStore } from 'pinia';
import { api } from 'boot/axios';

export type RegisterType =
  | 'coil'
  | 'discrete_input'
  | 'input_register'
  | 'holding_register';

type RegisterInput = string | number | null | undefined;

export interface ModuleRegister {
  name: string;
  register_type: RegisterType;
  address: number;
  length: number;
  description?: string;
  data_type?: string;
  transform?: string;
  on_value?: RegisterInput;
  off_value?: RegisterInput;
  [key: string]: RegisterInput;
}

export interface ModuleFeature {
  slug: string;
  description?: string;
  registers: ModuleRegister[];
  [key: string]: RegisterInput | ModuleRegister[];
}

export interface ModuleTypeConfig {
  slug: string;
  name: string;
  description?: string | null;
  registers: ModuleRegister[];
  meta?: Record<string, unknown>;
  kind?: string;
}

export interface ModuleConfig {
  slug: string;
  name: string;
  module_type?: string | null;
  description?: string | null;
  registers: ModuleRegister[];
  type_registers?: ModuleRegister[];
  actuators: ModuleFeature[];
  sensors: ModuleFeature[];
  meta?: Record<string, unknown>;
  kind?: string;
}

export const useModuleConfigStore = defineStore('moduleConfigs', {
  state: () => ({
    moduleTypes: [] as ModuleTypeConfig[],
    modules: [] as ModuleConfig[],
    loading: false,
    saving: false,
    error: null as string | null,
    restarting: false,
  }),

  actions: {
    async fetchModuleTypes() {
      this.loading = true;
      this.error = null;
      try {
        const response = await api.get<ModuleTypeConfig[]>('/module-configs/types');
        this.moduleTypes = response.data;
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось получить типы модулей');
      } finally {
        this.loading = false;
      }
    },

    async fetchModules() {
      this.loading = true;
      this.error = null;
      try {
        const response = await api.get<ModuleConfig[]>('/module-configs/modules');
        this.modules = response.data;
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось получить модули');
      } finally {
        this.loading = false;
      }
    },

    async refreshAll() {
      await Promise.all([this.fetchModuleTypes(), this.fetchModules()]);
    },

    async saveModuleType(payload: ModuleTypeConfig, overwrite = false) {
      this.saving = true;
      this.error = null;
      try {
        const endpoint = overwrite ? `/module-configs/types/${payload.slug}` : '/module-configs/types';
        const method = overwrite ? 'put' : 'post';
        await api.request({
          url: endpoint,
          method,
          data: payload,
        });
        await this.refreshAll();
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось сохранить тип модуля');
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async saveModule(payload: ModuleConfig, overwrite = false) {
      this.saving = true;
      this.error = null;
      try {
        const endpoint = overwrite ? `/module-configs/modules/${payload.slug}` : '/module-configs/modules';
        const method = overwrite ? 'put' : 'post';
        await api.request({
          url: endpoint,
          method,
          data: payload,
        });
        await this.refreshAll();
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось сохранить модуль');
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async deleteModuleType(slug: string) {
      this.saving = true;
      this.error = null;
      try {
        await api.delete(`/module-configs/types/${slug}`);
        await this.refreshAll();
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось удалить тип модуля');
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async deleteModule(slug: string) {
      this.saving = true;
      this.error = null;
      try {
        await api.delete(`/module-configs/modules/${slug}`);
        await this.refreshAll();
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось удалить модуль');
        throw error;
      } finally {
        this.saving = false;
      }
    },

    async requestRestart() {
      this.restarting = true;
      this.error = null;
      try {
        await api.post('/system/restart');
      } catch (error) {
        this.error = this.extractErrorMessage(error, 'Не удалось отправить команду перезапуска');
        throw error;
      } finally {
        this.restarting = false;
      }
    },

    extractErrorMessage(error: unknown, fallback: string): string {
      if (error && typeof error === 'object' && 'response' in error) {
        const response = (error as { response: { data?: { detail?: string; message?: string } } }).response;
        const detail = response?.data?.detail ?? response?.data?.message;
        if (detail) {
          return detail;
        }
      }
      return fallback;
    },
  },
});
