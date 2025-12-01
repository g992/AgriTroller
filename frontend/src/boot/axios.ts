import { defineBoot } from '#q-app/wrappers';
import axios, { type AxiosInstance } from 'axios';

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

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

  const buildFromWindow = (path = '/api') => {
    const url = new URL(typeof window !== 'undefined' ? window.location.href : 'http://localhost:8080');
    url.pathname = path.startsWith('/') ? path : `/${path}`;
    url.search = '';
    url.hash = '';
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
      } catch (err) {
        // fall back to window-based origin if parsing fails
        return buildFromWindow('/api');
      }
    }
    return envBase;
  }

  if (typeof window !== 'undefined') {
    return buildFromWindow('/api');
  }

  return 'http://localhost:8080/api';
}

const apiBaseUrl = resolveApiBaseUrl();

const api = axios.create({ baseURL: apiBaseUrl });

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
