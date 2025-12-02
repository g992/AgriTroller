import { defineBoot } from '#q-app/wrappers';
import { Notify } from 'quasar';
import axios, { type AxiosInstance } from 'axios';

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

const DEV_BACKEND_PORT = '8080';

// Be careful when using SSR for cross-request state pollution
// due to creating a Singleton instance here;
// If any client changes this (global) instance, it might be a
// good idea to move this instance creation inside of the
// "export default () => {}" function below (which runs individually
// for each client)
function resolveApiBaseUrl(): string {
  const envBase = import.meta.env.VITE_API_BASE_URL;

  const isLocalHost = (hostname: string) =>
    ['localhost', '127.0.0.1', '::1'].includes(hostname.toLowerCase());

  const buildFromWindow = (path = '/api', opts?: { port?: string }) => {
    const url = new URL(
      typeof window !== 'undefined' ? window.location.href : `http://localhost:${DEV_BACKEND_PORT}`,
    );
    url.pathname = path.startsWith('/') ? path : `/${path}`;
    url.search = '';
    url.hash = '';
    if (opts?.port) {
      url.port = opts.port;
    }
    return url.toString();
  };

  // If a base is provided, prefer it unless it points to localhost while the page is served from another host.
  if (envBase && envBase !== 'auto') {
    if (typeof window !== 'undefined') {
      try {
        const parsed = new URL(envBase, window.location.origin);
        if (isLocalHost(parsed.hostname) && !isLocalHost(window.location.hostname)) {
          return buildFromWindow(parsed.pathname || '/api');
        }
        return parsed.toString();
      } catch {
        return buildFromWindow('/api');
      }
    }
    return envBase;
  }

  if (typeof window !== 'undefined') {
    if (import.meta.env.DEV) {
      // When running the Vue dev server (port 9000), default API to backend on 8080
      return buildFromWindow('/api', { port: DEV_BACKEND_PORT });
    }
    return buildFromWindow('/api');
  }

  return `http://localhost:${DEV_BACKEND_PORT}/api`;
}

const apiBaseUrl = resolveApiBaseUrl();

const api = axios.create({ baseURL: apiBaseUrl });

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const response = error?.response;
    const status = response?.status;
    const detail =
      response?.data?.detail || response?.data?.message || response?.data?.error || error?.message;
    if (status && detail) {
      Notify.create({ message: detail, color: 'negative' });
    }
    return Promise.reject(error instanceof Error ? error : new Error(detail || 'Request failed'));
  },
);

export default defineBoot(({ app }) => {
  // for use inside Vue files (Options API) through this.$axios and this.$api

  app.config.globalProperties.$axios = axios;
  // ^ ^ ^ this will allow you to use this.$axios (for Vue Options API form)
  //       so you won't necessarily have to import axios in each vue file

  app.config.globalProperties.$api = api;
  // ^ ^ ^ this will allow you to use this.$api (for Vue Options API form)
  //       so you can easily perform requests against your app's API
});

export { api };
