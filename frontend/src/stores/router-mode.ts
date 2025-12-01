import { defineStore } from 'pinia';

export type UiMode = 'kiosk' | 'default';

const STORAGE_KEY = 'agritroller:lastMode';

const normalize = (value: unknown): UiMode | null => {
  if (typeof value !== 'string') return null;
  const v = value.toLowerCase();
  if (v === 'kiosk') return 'kiosk';
  if (['default', 'normal', 'app'].includes(v)) return 'default';
  return null;
};

export const useRouterMode = defineStore('routerMode', {
  state: () => ({
    mode: normalize(localStorage.getItem(STORAGE_KEY)) ?? 'default',
  }),
  actions: {
    setMode(mode: UiMode) {
      this.mode = mode;
      localStorage.setItem(STORAGE_KEY, mode);
    },
  },
});
