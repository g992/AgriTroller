import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/HomePage.vue') },
      { path: 'settings', component: () => import('pages/SettingsPage.vue') },
    ],
  },

  {
    path: '/kiosk',
    component: () => import('layouts/KioskLayout.vue'),
    children: [
      { path: '', component: () => import('pages/kiosk/KioskHomePage.vue') },
      { path: 'settings', component: () => import('pages/kiosk/KioskSettingsPage.vue') },
    ],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
