import { defineRouter } from '#q-app/wrappers';
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
  NavigationGuardNext,
  RouteLocationNormalized,
} from 'vue-router';
import routes from './routes';

/*
 * If not building with SSR mode, you can
 * directly export the Router instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Router instance.
 */

export default defineRouter(function (/* { store, ssrContext } */) {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : process.env.VUE_ROUTER_MODE === 'history'
      ? createWebHistory
      : createWebHashHistory;

  const LAST_MODE_KEY = 'agritroller:lastMode';
  type ModeName = 'kiosk' | 'default';

  const normalizeMode = (value: unknown): ModeName | null => {
    if (typeof value !== 'string') return null;
    const v = value.toLowerCase();
    if (v === 'kiosk') return 'kiosk';
    if (['default', 'normal', 'app'].includes(v)) return 'default';
    return null;
  };

  const getLastMode = (): ModeName | null => {
    if (typeof window === 'undefined' || !window.localStorage) return null;
    const stored = window.localStorage.getItem(LAST_MODE_KEY);
    return normalizeMode(stored);
  };

  const setLastMode = (mode: ModeName): void => {
    if (typeof window === 'undefined' || !window.localStorage) return;
    window.localStorage.setItem(LAST_MODE_KEY, mode);
  };

  const ensureMode = (
    to: RouteLocationNormalized,
    next: NavigationGuardNext,
    forcedMode?: ModeName | null,
  ) => {
    const removeModeQuery = { ...to.query };
    delete removeModeQuery.mode;

    const targetMode: ModeName | null = forcedMode ?? getLastMode();
    if (targetMode === 'kiosk' && !to.path.startsWith('/kiosk')) {
      setLastMode('kiosk');
      next({ path: '/kiosk', query: removeModeQuery, hash: to.hash });
      return true;
    }
    return false;
  };

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,

    // Leave this as is and make changes in quasar.conf.js instead!
    // quasar.conf.js -> build -> vueRouterMode
    // quasar.conf.js -> build -> publicPath
    history: createHistory(process.env.VUE_ROUTER_BASE),
  });

  Router.beforeEach((to, from, next) => {
    const queryMode = normalizeMode(to.query.mode);

    if (queryMode) {
      setLastMode(queryMode);
      const redirected = ensureMode(to, next, queryMode);
      if (redirected) return;
      // If already in target mode, strip mode from URL to avoid loops.
      const cleanedQuery = { ...to.query };
      delete cleanedQuery.mode;
      next({ path: to.path, query: cleanedQuery, hash: to.hash, params: to.params });
      return;
    }

    const redirected = ensureMode(to, next);
    if (redirected) return;

    // Persist mode based on current route when no redirect happened.
    if (to.path.startsWith('/kiosk')) {
      setLastMode('kiosk');
    } else if (!to.path.startsWith('/api')) {
      setLastMode('default');
    }

    next();
  });

  return Router;
});
