<template>
  <q-page class="settings-page q-pa-lg">
    <div class="settings-container">
      <div class="row items-center justify-between q-mb-lg">
        <div>
          <div class="text-h4 text-white text-weight-bold">Настройки</div>
          <div class="text-subtitle2 text-grey-5">
            Управление версиями, устройствами и коммуникационными портами
          </div>
        </div>
        <q-btn color="secondary" outline icon="refresh" :loading="isRefreshing" @click="refresh">
          обновить
        </q-btn>
      </div>

      <q-banner v-if="lastError" rounded dense class="bg-red-10 text-white q-mb-lg">
        {{ lastError }}
      </q-banner>

      <div class="settings-layout row q-col-gutter-xl">
        <div class="col-12 col-lg-9">
        <q-tab-panels v-model="activeTab" animated class="main-panels">
          <q-tab-panel name="general">
            <section class="q-mb-xl">
              <div class="section-title">Версии компонентов</div>
              <div class="section-subtitle">Текущие сборки backend, frontend и прошивки</div>
              <div class="row q-col-gutter-lg q-mt-md">
                <div class="col-12 col-md-4" v-for="card in versionCards" :key="card.label">
                  <StatusCard :label="card.label" :value="card.value" :icon="card.icon">
                    <div class="text-caption text-grey-5">{{ card.caption }}</div>
                  </StatusCard>
                </div>
              </div>
            </section>

            <section>
              <div class="section-title">Нагрузка системы</div>
              <div class="section-subtitle">
                Показатели CPU, оперативной памяти, накопителя и размер базы данных
              </div>
              <q-card class="dashboard-card q-mt-md">
                <q-card-section>
                  <div class="row q-col-gutter-lg">
                    <div class="col-12 col-md-6">
                      <div class="metric-label">CPU</div>
                      <div class="metric-value">{{ cpuUsage }}</div>
                      <div class="text-caption text-grey-5">
                        {{ cpuDetails }}
                      </div>
                    </div>
                    <div class="col-12 col-md-6">
                      <div class="metric-label">Память (RAM)</div>
                      <div class="metric-value">{{ memoryUsage }}</div>
                      <div class="text-caption text-grey-5">{{ memoryDetails }}</div>
                    </div>
                  </div>
                  <q-separator dark spaced />
                  <div class="row q-col-gutter-lg">
                    <div class="col-12 col-md-6">
                      <div class="metric-label">Накопитель</div>
                      <div class="metric-value">{{ storageUsage }}</div>
                      <div class="text-caption text-grey-5">{{ storageDetails }}</div>
                    </div>
                    <div class="col-12 col-md-6">
                      <div class="metric-label">База данных</div>
                      <div class="metric-value">{{ dbSize }}</div>
                      <div class="text-caption text-grey-5">{{ dbPath }}</div>
                    </div>
                  </div>
                </q-card-section>
              </q-card>
            </section>
          </q-tab-panel>

          <q-tab-panel name="wifi">
            <div class="section-title">Wi-Fi подключение</div>
            <div class="section-subtitle">
              Выберите сеть, введите пароль и подключите контроллер к инфраструктуре.
            </div>

            <q-card class="dashboard-card q-mt-md">
              <q-card-section class="row items-center justify-between">
                <div>
                  <div class="text-subtitle1 text-white">Доступные сети</div>
                  <div class="text-caption text-grey-5">Сканирование адаптера Wi-Fi</div>
                </div>
                <div class="row items-center q-gutter-sm">
                  <q-btn
                    dense
                    flat
                    color="primary"
                    icon="refresh"
                    label="сканировать"
                    :loading="wifiLoading"
                    :disable="wifiConnecting"
                    @click="refreshWifiNetworks"
                  />
                  <q-btn
                    dense
                    flat
                    color="secondary"
                    icon="wifi"
                    label="статус"
                    :loading="wifiLoading"
                    :disable="wifiConnecting"
                    @click="refreshWifiStatus"
                  />
                </div>
              </q-card-section>
              <q-separator dark />
              <q-card-section>
                <q-banner
                  v-if="wifiError"
                  dense
                  rounded
                  class="bg-red-10 text-white q-mb-md"
                >
                  {{ wifiError }}
                </q-banner>
                <div v-if="wifiLoading" class="row justify-center q-my-lg">
                  <q-spinner color="primary" size="36px" />
                </div>
                <div v-else>
                  <div v-if="!sortedWifiNetworks.length" class="text-grey-6">
                    Сети не найдены. Попробуйте обновить список.
                  </div>
                  <q-list v-else bordered separator dense class="rounded-borders">
                    <q-item
                      v-for="network in sortedWifiNetworks"
                      :key="network.ssid"
                      clickable
                      v-ripple
                      :active="wifiForm.ssid === network.ssid"
                      active-class="sidebar-active"
                      @click="selectWifiNetwork(network.ssid)"
                    >
                      <q-item-section avatar>
                        <q-icon
                          :name="network.active ? 'wifi_tethering' : 'wifi'"
                          :color="network.active ? 'positive' : 'primary'"
                        />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-white text-weight-medium">
                          {{ network.ssid }}
                        </q-item-label>
                        <q-item-label caption class="text-grey-5">
                          {{ network.security || 'open' }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side top>
                        <div class="text-caption text-grey-5 text-right">
                          {{ network.signal }}%
                        </div>
                        <q-linear-progress
                          :value="Math.min(1, Math.max(0, network.signal / 100))"
                          color="primary"
                          track-color="grey-9"
                          size="10px"
                        />
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="dashboard-card q-mt-lg">
              <q-card-section>
                <div class="row items-center justify-between q-mb-sm">
                  <div>
                    <div class="text-subtitle1 text-white">Подключение</div>
                    <div class="text-caption text-grey-5">
                      Текущий статус: {{ wifiStatusLabel }}
                    </div>
                  </div>
                  <q-chip
                    square
                    :color="wifiStatusColor"
                    text-color="black"
                    icon="radio_button_checked"
                  >
                    {{ wifiStatusLabel }}
                  </q-chip>
                </div>
                <div class="text-grey-5 text-caption q-mb-md">
                  {{ wifiStatusDetails }}
                </div>
                <q-banner v-if="wifiConnectError" dense rounded class="bg-red-10 text-white q-mb-md">
                  {{ wifiConnectError }}
                </q-banner>
                <q-form @submit.prevent="submitWifiConnect" class="row q-col-gutter-md">
                  <div class="col-12 col-md-5">
                    <q-input
                      v-model="wifiForm.ssid"
                      label="SSID"
                      standout="bg-dark"
                      stack-label
                      dense
                      :disable="wifiConnecting"
                      required
                    />
                  </div>
                  <div class="col-12 col-md-5">
                    <q-input
                      v-model="wifiForm.password"
                      :type="showWifiPassword ? 'text' : 'password'"
                      label="Пароль (если требуется)"
                      standout="bg-dark"
                      stack-label
                      dense
                      :disable="wifiConnecting"
                      autocomplete="off"
                    >
                      <template #append>
                        <q-icon
                          :name="showWifiPassword ? 'visibility_off' : 'visibility'"
                          class="cursor-pointer"
                          @click="showWifiPassword = !showWifiPassword"
                        />
                      </template>
                    </q-input>
                  </div>
                  <div class="col-12 col-md-2 flex items-end">
                    <q-btn
                      type="submit"
                      color="primary"
                      label="Подключить"
                      class="full-width"
                      :loading="wifiConnecting"
                      :disable="wifiConnecting"
                    />
                  </div>
                </q-form>
              </q-card-section>
            </q-card>
          </q-tab-panel>

      <q-tab-panel name="ports">
        <div class="section-title">UART порты</div>
        <div class="section-subtitle">
          Управляйте периферийными контроллерами и RS-485 шлюзами, добавляйте новые линии связи и задавайте скорость обмена.
        </div>
        <q-card class="dashboard-card q-mt-md">
          <q-card-section>
            <q-banner
              v-if="devicesError"
              dense
              rounded
              class="bg-red-10 text-white q-mb-md"
            >
              {{ devicesError }}
            </q-banner>
            <div v-if="devicesLoading" class="row justify-center q-my-xl">
              <q-spinner color="primary" size="42px" />
            </div>
            <div v-else class="row q-col-gutter-lg">
              <div class="col-12 col-md-6">
                <div class="ports-subtitle">Периферийные контроллеры</div>
                <div v-if="!peripheralDevices.length" class="text-grey-6 text-caption q-mt-md">
                  Контроллеры ещё не добавлены.
                </div>
                <q-list
                  v-else
                  dense
                  bordered
                  separator
                  class="rounded-borders q-mt-md"
                >
                  <q-item v-for="device in peripheralDevices" :key="device.id">
                    <q-item-section avatar>
                      <q-icon name="memory" color="primary" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-white text-weight-medium">
                        {{ device.name }}
                      </q-item-label>
                      <q-item-label caption class="text-grey-5">
                        {{ device.port }} · {{ device.baudrate.toLocaleString('ru-RU') }} бод
                      </q-item-label>
                      <q-item-label caption class="text-grey-6">
                        Статус: {{ statusLabel(device.status) }} ·
                        {{ device.status_message || 'ещё не проверялся' }}
                      </q-item-label>
                      <q-item-label caption class="text-grey-7">
                        Проверено: {{ formatStatusTimestamp(device.status_checked_at) }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-chip
                        square
                        :color="statusColor(device.status)"
                        text-color="black"
                        size="sm"
                      >
                        {{ statusLabel(device.status) }}
                      </q-chip>
                      <q-chip
                        square
                        :color="device.enabled ? 'positive' : 'warning'"
                        text-color="black"
                        size="sm"
                      >
                        {{ device.enabled ? 'активен' : 'отключен' }}
                      </q-chip>
                    </q-item-section>
                    <q-item-section side top>
                      <div class="row items-center no-wrap q-gutter-xs">
                        <q-btn
                          dense
                          flat
                          round
                          icon="refresh"
                          color="accent"
                          :loading="isDeviceRefreshing(device.id)"
                          :disable="devicesSaving || isDeviceRefreshing(device.id)"
                          @click="refreshDeviceStatus(device.id)"
                        />
                        <q-btn
                          dense
                          flat
                          round
                          color="primary"
                          icon="edit"
                          :disable="devicesSaving"
                          @click="openEditDialog(device)"
                        />
                        <q-btn
                          dense
                          flat
                          round
                          color="negative"
                          icon="delete"
                          :disable="devicesSaving"
                          @click="requestDelete(device)"
                        />
                      </div>
                    </q-item-section>
                  </q-item>
                </q-list>
              </div>
              <div class="col-12 col-md-6">
                <div class="ports-subtitle">RS-485 шлюзы</div>
                <div v-if="!rs485Devices.length" class="text-grey-6 text-caption q-mt-md">
                  Шлюзы ещё не добавлены.
                </div>
                <q-list
                  v-else
                  dense
                  bordered
                  separator
                  class="rounded-borders q-mt-md"
                >
                  <q-item v-for="device in rs485Devices" :key="device.id">
                    <q-item-section avatar>
                      <q-icon name="device_hub" color="secondary" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-white text-weight-medium">
                        {{ device.name }}
                      </q-item-label>
                      <q-item-label caption class="text-grey-5">
                        {{ device.port }} · {{ device.baudrate.toLocaleString('ru-RU') }} бод
                      </q-item-label>
                      <q-item-label caption class="text-grey-6">
                        Статус: {{ statusLabel(device.status) }} ·
                        {{ device.status_message || 'ещё не проверялся' }}
                      </q-item-label>
                      <q-item-label caption class="text-grey-7">
                        Проверено: {{ formatStatusTimestamp(device.status_checked_at) }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-chip
                        square
                        :color="statusColor(device.status)"
                        size="sm"
                        text-color="white"
                      >
                        {{ statusLabel(device.status) }}
                      </q-chip>
                      <q-chip
                        square
                        :color="device.enabled ? 'primary' : 'warning'"
                        size="sm"
                        text-color="white"
                      >
                        {{ device.enabled ? 'активен' : 'отключен' }}
                      </q-chip>
                    </q-item-section>
                    <q-item-section side top>
                      <div class="row items-center no-wrap q-gutter-xs">
                        <q-btn
                          dense
                          flat
                          round
                          icon="refresh"
                          color="accent"
                          :loading="isDeviceRefreshing(device.id)"
                          :disable="devicesSaving || isDeviceRefreshing(device.id)"
                          @click="refreshDeviceStatus(device.id)"
                        />
                        <q-btn
                          dense
                          flat
                          round
                          color="secondary"
                          icon="edit"
                          :disable="devicesSaving"
                          @click="openEditDialog(device)"
                        />
                        <q-btn
                          dense
                          flat
                          round
                          color="negative"
                          icon="delete"
                          :disable="devicesSaving"
                          @click="requestDelete(device)"
                        />
                      </div>
                    </q-item-section>
                  </q-item>
                </q-list>
              </div>
            </div>
          </q-card-section>
        </q-card>

        <q-card class="dashboard-card q-mt-lg">
          <q-card-section>
            <div class="section-title q-mb-md">Добавить UART порт</div>
            <q-banner
              v-if="portFormError"
              dense
              rounded
              class="bg-red-10 text-white q-mb-md"
            >
              {{ portFormError }}
            </q-banner>
            <q-form @submit.prevent="submitPort" class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="portForm.name"
                  label="Название"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="devicesSaving"
                  maxlength="64"
                  counter
                  required
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="portForm.kind"
                  :options="portTypeOptions"
                  emit-value
                  map-options
                  label="Тип порта"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="devicesSaving"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="portForm.port"
                  :options="filteredPortOptions"
                  use-input
                  hide-selected
                  fill-input
                  input-debounce="0"
                  label="Системный путь"
                  standout="bg-dark"
                  stack-label
                  dense
                :disable="devicesSaving"
                :loading="portsLoading"
                @filter="filterPortOptions"
                @input-value="handlePortInput"
                @new-value="handlePortNewValue"
              >
                  <template #no-option>
                    <q-item>
                      <q-item-section class="text-grey-6">
                        Нет подходящих портов — введите путь вручную и нажмите Enter
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model.number="portForm.baudrate"
                  type="number"
                  label="Скорость (бод)"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="devicesSaving"
                  min="300"
                  step="300"
                  required
                />
              </div>
              <div class="col-12 col-md-6">
                <!-- device type selection removed; using default generic_empty -->
              </div>
              <div class="col-12">
                <q-btn
                  type="submit"
                  color="primary"
                  label="Добавить порт"
                  :loading="devicesSaving"
                  :disable="devicesSaving"
                />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="scanner">
        <div class="section-title">Modbus сканер</div>
        <div class="section-subtitle">
          Поиск устройств по адресу/регистру, контроль прогресса и быстрая привязка типа.
        </div>
        <q-card class="dashboard-card q-mt-md">
          <q-card-section>
            <q-banner
              v-if="scanError"
              dense
              rounded
              class="bg-red-10 text-white q-mb-md"
            >
              {{ scanError }}
            </q-banner>
            <q-form @submit.prevent="runScan" class="row q-col-gutter-md">
              <div class="col-12 col-md-4">
                <q-select
                  v-model="scanForm.deviceId"
                  :options="rs485DeviceOptions"
                  emit-value
                  map-options
                  option-label="label"
                  option-value="value"
                  label="RS-485 устройство"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  :loading="devicesLoading"
                />
              </div>
              <div class="col-12 col-md-2">
                <q-input
                  v-model.number="scanForm.baudrate"
                  type="number"
                  label="Скорость (бод)"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  min="1200"
                  step="600"
                />
              </div>
              <div class="col-6 col-md-2">
                <q-input
                  v-model.number="scanForm.startAddress"
                  type="number"
                  label="Адрес от"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  min="1"
                  max="247"
                  required
                />
              </div>
              <div class="col-6 col-md-2">
                <q-input
                  v-model.number="scanForm.endAddress"
                  type="number"
                  label="Адрес до"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  min="1"
                  max="247"
                  required
                />
              </div>
              <div class="col-6 col-md-2">
                <q-input
                  v-model.number="scanForm.register"
                  type="number"
                  label="Регистр"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  min="0"
                  max="65535"
                  required
                />
              </div>
              <div class="col-6 col-md-2">
                <q-input
                  v-model.number="scanForm.count"
                  type="number"
                  label="Слов"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  min="1"
                  max="4"
                />
              </div>
              <div class="col-12 col-md-3">
                <q-input
                  v-model.number="scanForm.timeout"
                  type="number"
                  label="Таймаут (сек)"
                  standout="bg-dark"
                  stack-label
                  dense
                  :disable="scanLoading"
                  min="0.05"
                  step="0.05"
                />
              </div>
              <div class="col-12 col-md-3 flex items-end">
                <q-btn
                  type="submit"
                  color="primary"
                  label="Сканировать"
                  :loading="scanLoading"
                  :disable="scanLoading"
                  class="full-width"
                />
              </div>
            </q-form>
            <div v-if="scanJob" class="q-mt-md">
              <div class="row items-center justify-between q-mb-sm">
                <div class="text-white text-weight-medium">
                  Статус: {{ scanJob.status }}
                </div>
                <q-chip v-if="scanJob.error" square color="negative" text-color="white">
                  {{ scanJob.error }}
                </q-chip>
              </div>
              <q-linear-progress
                :value="scanProgress"
                color="primary"
                track-color="grey-9"
                animated
              />
              <div class="text-grey-5 text-caption q-mt-xs">
                {{ scanJob.progress }} / {{ scanJob.total }} адресов
              </div>
            </div>
          </q-card-section>
        </q-card>

        <q-card class="dashboard-card q-mt-md">
          <q-card-section>
            <div class="row items-center justify-between q-mb-sm">
              <div class="section-title q-mb-none">Найденные устройства</div>
              <q-btn
                v-if="scanJob && scanJob.status === 'completed'"
                flat
                dense
                icon="refresh"
                label="повторить"
                @click="resetScan"
              />
            </div>
            <div v-if="!scanResults.length" class="text-grey-6">
              Пока ничего не найдено. Запустите сканирование.
            </div>
            <q-list v-else bordered separator dense class="rounded-borders">
              <q-item v-for="result in scanResults" :key="`${result.address}-${result.register}`">
                <q-item-section avatar>
                  <q-icon name="radar" color="primary" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-white text-weight-medium">
                    Адрес {{ result.address }} · регистр {{ result.register }}
                  </q-item-label>
                  <q-item-label caption class="text-grey-5">
                    Значение: {{ result.value }} · RAW: {{ result.raw }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    color="positive"
                    dense
                    flat
                    icon="add"
                    label="Создать"
                    class="q-mt-xs"
                    :loading="devicesSaving"
                    :disable="devicesSaving"
                    @click="createDeviceFromResult(result)"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="modules">
        <div class="section-title">Модули и типы (.cfg)</div>
        <div class="section-subtitle">
          Файлы конфигураций на диске ({{ moduleConfigPath }}). Изменения требуют перезапуска.
        </div>
        <q-banner
          v-if="moduleError"
          dense
          rounded
          class="bg-red-10 text-white q-mt-md"
        >
          {{ moduleError }}
        </q-banner>
        <div class="row q-col-gutter-lg q-mt-md">
          <div class="col-12 col-lg-6">
            <q-card class="dashboard-card">
              <q-card-section>
                <div class="row items-center justify-between q-mb-sm">
                  <div>
                    <div class="text-white text-weight-medium">Типы модулей</div>
                    <div class="text-caption text-grey-5">Базовые регистры и общие поля</div>
                  </div>
                  <q-btn color="primary" icon="add" label="Создать" dense @click="openModuleTypeDialog()" />
                </div>
                <div v-if="moduleLoading" class="row justify-center q-my-lg">
                  <q-spinner color="primary" size="32px" />
                </div>
                <q-list v-else bordered separator dense class="rounded-borders">
                  <q-item v-for="type in moduleTypes" :key="type.slug">
                    <q-item-section avatar>
                      <q-icon name="schema" color="secondary" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-white text-weight-medium">
                        {{ type.name }} <span class="text-grey-6">({{ type.slug }})</span>
                      </q-item-label>
                      <q-item-label caption class="text-grey-5">
                        Регистры: {{ type.registers?.length || 0 }}
                      </q-item-label>
                      <q-item-label caption class="text-grey-6" v-if="type.description">
                        {{ type.description }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <div class="row items-center q-gutter-xs">
                        <q-btn dense flat round icon="edit" color="primary" @click="openModuleTypeDialog(type)" />
                        <q-btn dense flat round icon="delete" color="negative" :disable="moduleSaving" @click="deleteModuleType(type.slug)" />
                      </div>
                    </q-item-section>
                  </q-item>
                  <q-item v-if="!moduleTypes.length">
                    <q-item-section>
                      <q-item-label class="text-grey-6">Пока нет пользовательских типов.</q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-card-section>
            </q-card>
          </div>

          <div class="col-12 col-lg-6">
            <q-card class="dashboard-card">
              <q-card-section>
                <div class="row items-center justify-between q-mb-sm">
                  <div>
                    <div class="text-white text-weight-medium">Модули</div>
                    <div class="text-caption text-grey-5">Актуаторы, сенсоры и их регистры</div>
                  </div>
                  <q-btn color="primary" icon="add" label="Создать" dense @click="openModuleDialog()" />
                </div>
                <div v-if="moduleLoading" class="row justify-center q-my-lg">
                  <q-spinner color="primary" size="32px" />
                </div>
                <q-list v-else bordered separator dense class="rounded-borders">
                  <q-item v-for="module in modules" :key="module.slug">
                    <q-item-section avatar>
                      <q-icon name="memory" color="accent" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-white text-weight-medium">
                        {{ module.name }} <span class="text-grey-6">({{ module.slug }})</span>
                      </q-item-label>
                      <q-item-label caption class="text-grey-5">
                        Тип: {{ module.module_type || '—' }} · Регистров: {{ module.registers?.length || 0 }} · Актуа.: {{ module.actuators?.length || 0 }} · Сенс.: {{ module.sensors?.length || 0 }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <div class="row items-center q-gutter-xs">
                        <q-btn dense flat round icon="edit" color="primary" @click="openModuleDialog(module)" />
                        <q-btn dense flat round icon="delete" color="negative" :disable="moduleSaving" @click="deleteModule(module.slug)" />
                      </div>
                    </q-item-section>
                  </q-item>
                  <q-item v-if="!modules.length">
                    <q-item-section>
                      <q-item-label class="text-grey-6">Модули пока не описаны.</q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>

                <div class="row items-center q-gutter-sm q-mt-md">
                  <q-btn
                    outline
                    color="secondary"
                    icon="refresh"
                    label="Перечитать cfg"
                    :loading="moduleLoading"
                    @click="refreshModuleConfigs"
                  />
                  <q-btn
                    color="negative"
                    icon="restart_alt"
                    label="Перезапуск"
                    :loading="moduleRestarting"
                    @click="requestRestart"
                  />
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-tab-panel>

    </q-tab-panels>
      </div>

        <div class="col-12 col-lg-3">
        <q-card class="sidebar-card">
          <q-card-section>
            <div class="text-subtitle1 text-white">Разделы</div>
            <div class="text-caption text-grey-5">Быстрые переходы по настройкам</div>
          </q-card-section>
          <q-separator dark />
          <q-list class="sidebar-nav">
            <q-item
              v-for="section in settingsSections"
              :key="section.name"
              clickable
              v-ripple
              :active="activeTab === section.name"
              active-class="sidebar-active"
              @click="setTab(section.name)"
            >
              <q-item-section avatar>
                <q-icon :name="section.icon" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-white text-weight-medium">
                  {{ section.label }}
                </q-item-label>
                <q-item-label caption class="text-grey-5">
                  {{ section.caption }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon
                  name="chevron_right"
                  size="16px"
                  :class="['text-grey-6', { 'text-primary': activeTab === section.name }]"
                />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        </div>
      </div>
    </div>
    <q-dialog v-model="isEditDialogOpen">
      <q-card class="edit-dialog-card">
        <q-card-section>
          <div class="text-h6 text-white">Редактировать UART порт</div>
          <div class="text-caption text-grey-5">
            Измените параметры подключения и сохраните для применения.
          </div>
        </q-card-section>
        <q-card-section>
          <q-banner
            v-if="editFormError"
            dense
            rounded
            class="bg-red-10 text-white q-mb-md"
          >
            {{ editFormError }}
          </q-banner>
          <q-form @submit.prevent="submitEditForm" class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <q-input
                v-model="editForm.name"
                label="Название"
                standout="bg-dark"
                stack-label
                dense
                :disable="devicesSaving"
                maxlength="64"
                counter
                required
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="editForm.kind"
                :options="portTypeOptions"
                emit-value
                map-options
                label="Тип порта"
                standout="bg-dark"
                stack-label
                dense
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="editForm.port"
                :options="filteredPortOptions"
                use-input
                hide-selected
                fill-input
                input-debounce="0"
                label="Системный путь"
                standout="bg-dark"
                stack-label
                dense
                :disable="devicesSaving"
                :loading="portsLoading"
                @filter="filterPortOptions"
                @input-value="handleEditPortInput"
                @new-value="handlePortNewValue"
              >
                <template #no-option>
                  <q-item>
                    <q-item-section class="text-grey-6">
                      Нет подходящих портов — введите путь вручную и нажмите Enter
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>
            </div>
            <div class="col-12 col-md-6">
              <q-input
                v-model.number="editForm.baudrate"
                type="number"
                label="Скорость (бод)"
                standout="bg-dark"
                stack-label
                dense
                :disable="devicesSaving"
                min="300"
                step="300"
                required
              />
            </div>
            <div class="col-12 col-md-6">
              <!-- device type selection removed; using default generic_empty -->
            </div>
            <div class="col-12">
              <q-toggle
                v-model="editForm.enabled"
                color="positive"
                label="Порт активен"
                :disable="devicesSaving"
              />
            </div>
            <div class="col-12 q-gutter-sm text-right">
              <q-btn
                flat
                label="Отмена"
                color="white"
                :disable="devicesSaving"
                @click="closeEditDialog"
              />
              <q-btn
                type="submit"
                color="primary"
                label="Сохранить"
                :loading="devicesSaving"
                :disable="devicesSaving"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="isDeleteDialogOpen">
      <q-card class="delete-dialog-card">
        <q-card-section class="row items-start q-gutter-sm">
          <q-icon name="warning" color="warning" size="32px" />
          <div>
            <div class="text-h6 text-white">Удалить устройство?</div>
            <div class="text-grey-5">
              Это действие необратимо. Порт
              <strong>{{ deleteTarget ? deleteTarget.name : 'без названия' }}</strong> будет удалён из реестра.
            </div>
          </div>
        </q-card-section>
        <q-card-section v-if="deleteError">
          <q-banner dense rounded class="bg-red-10 text-white">
            {{ deleteError }}
          </q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            flat
            label="Отмена"
            color="white"
            :disable="devicesSaving"
            @click="closeDeleteDialog"
          />
          <q-btn
            color="negative"
            label="Удалить"
            :loading="devicesSaving"
            :disable="devicesSaving"
            @click="confirmDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="isModuleTypeDialogOpen" persistent>
      <q-card class="edit-dialog-card">
        <q-card-section>
          <div class="text-h6 text-white">
            {{ moduleTypeDialogMode === 'create' ? 'Создать тип модуля' : 'Редактировать тип модуля' }}
          </div>
          <div class="text-caption text-grey-5">Базовые регистры и описание типа.</div>
        </q-card-section>
        <q-card-section>
          <q-banner v-if="moduleFormError" dense rounded class="bg-red-10 text-white q-mb-md">
            {{ moduleFormError }}
          </q-banner>
          <q-form @submit.prevent="submitModuleType">
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <q-input v-model="moduleTypeForm.slug" label="Slug" standout="bg-dark" dense :disable="moduleTypeDialogMode === 'edit'" required />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="moduleTypeForm.name" label="Название" standout="bg-dark" dense required />
              </div>
              <div class="col-12">
                <q-input v-model="moduleTypeForm.description" label="Описание" standout="bg-dark" dense />
              </div>
              <div class="col-12">
                <div class="text-subtitle2 text-white q-mb-sm">Регистры</div>
                <div v-for="(register, idx) in moduleTypeForm.registers" :key="`type-reg-${idx}`" class="q-mb-sm">
                  <q-card flat bordered class="bg-dark-2">
                    <q-card-section>
                      <div class="row q-col-gutter-sm items-center">
                        <div class="col-12 col-md-3">
                          <q-input v-model="register.name" label="Имя" dense standout="bg-dark" required />
                        </div>
                        <div class="col-12 col-md-3">
                          <q-select v-model="register.register_type" :options="registerTypeOptions" emit-value map-options label="Тип" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-2">
                          <q-input v-model.number="register.address" type="number" label="Адрес" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-2">
                          <q-input v-model.number="register.length" type="number" label="Длина" dense standout="bg-dark" min="1" />
                        </div>
                        <div class="col-12 col-md-2 text-right">
                          <q-btn dense flat round icon="delete" color="negative" @click="removeRegister(moduleTypeForm.registers, idx)" />
                        </div>
                        <div class="col-12 col-md-6">
                          <q-input v-model="register.description" label="Описание" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-3">
                          <q-input v-model="register.data_type" label="Тип данных" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-3">
                          <q-input v-model="register.transform" label="Преобразование" dense standout="bg-dark" />
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>
                <q-btn flat color="primary" icon="add" label="Добавить регистр" @click="addRegister(moduleTypeForm.registers)" />
              </div>
            </div>
            <div class="row q-col-gutter-md q-mt-md">
              <div class="col-12 col-md-6">
                <q-btn type="submit" color="primary" label="Сохранить" :loading="moduleSaving" class="full-width" />
              </div>
              <div class="col-12 col-md-6">
                <q-btn flat color="grey-5" label="Отмена" class="full-width" @click="closeModuleTypeDialog" />
              </div>
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="isModuleDialogOpen" persistent>
      <q-card class="edit-dialog-card">
        <q-card-section>
          <div class="text-h6 text-white">
            {{ moduleDialogMode === 'create' ? 'Создать модуль' : 'Редактировать модуль' }}
          </div>
          <div class="text-caption text-grey-5">Опишите регистры модуля, сенсоров и актуаторов.</div>
        </q-card-section>
        <q-card-section>
          <q-banner v-if="moduleFormError" dense rounded class="bg-red-10 text-white q-mb-md">
            {{ moduleFormError }}
          </q-banner>
          <q-form @submit.prevent="submitModule">
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-4">
                <q-input v-model="moduleForm.slug" label="Slug" standout="bg-dark" dense :disable="moduleDialogMode === 'edit'" required />
              </div>
              <div class="col-12 col-md-4">
                <q-input v-model="moduleForm.name" label="Название" standout="bg-dark" dense required />
              </div>
              <div class="col-12 col-md-4">
                <q-select
                  v-model="moduleForm.module_type"
                  :options="moduleTypeSelectOptions"
                  emit-value
                  map-options
                  label="Тип модуля"
                  standout="bg-dark"
                  dense
                  clearable
                />
              </div>
              <div class="col-12">
                <q-input v-model="moduleForm.description" label="Описание" standout="bg-dark" dense />
              </div>

              <div class="col-12">
                <div class="text-subtitle2 text-white q-mb-sm">Регистры модуля</div>
                <div v-for="(register, idx) in moduleForm.registers" :key="`module-reg-${idx}`" class="q-mb-sm">
                  <q-card flat bordered class="bg-dark-2">
                    <q-card-section>
                      <div class="row q-col-gutter-sm items-center">
                        <div class="col-12 col-md-3">
                          <q-input v-model="register.name" label="Имя" dense standout="bg-dark" required />
                        </div>
                        <div class="col-12 col-md-3">
                          <q-select v-model="register.register_type" :options="registerTypeOptions" emit-value map-options label="Тип" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-2">
                          <q-input v-model.number="register.address" type="number" label="Адрес" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-2">
                          <q-input v-model.number="register.length" type="number" label="Длина" dense standout="bg-dark" min="1" />
                        </div>
                        <div class="col-12 col-md-2 text-right">
                          <q-btn dense flat round icon="delete" color="negative" @click="removeRegister(moduleForm.registers, idx)" />
                        </div>
                        <div class="col-12 col-md-6">
                          <q-input v-model="register.description" label="Описание" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-3">
                          <q-input v-model="register.data_type" label="Тип данных" dense standout="bg-dark" />
                        </div>
                        <div class="col-6 col-md-3">
                          <q-input v-model="register.transform" label="Преобразование" dense standout="bg-dark" />
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>
                <q-btn flat color="primary" icon="add" label="Добавить регистр" @click="addRegister(moduleForm.registers)" />
              </div>

              <div class="col-12">
                <div class="text-subtitle2 text-white q-mb-sm">Актуаторы</div>
                <div v-for="(act, idx) in moduleForm.actuators" :key="`act-${idx}`" class="q-mb-sm">
                  <q-card flat bordered class="bg-dark-2">
                    <q-card-section>
                      <div class="row q-col-gutter-sm items-center q-mb-sm">
                        <div class="col-12 col-md-4">
                          <q-input v-model="act.slug" label="Имя актуатора" dense standout="bg-dark" />
                        </div>
                        <div class="col-12 col-md-4">
                          <q-input v-model="act.description" label="Описание" dense standout="bg-dark" />
                        </div>
                        <div class="col-12 col-md-4 text-right">
                          <q-btn dense flat round icon="delete" color="negative" @click="removeFeature(moduleForm.actuators, idx)" />
                        </div>
                      </div>
                      <div v-for="(register, rIdx) in act.registers" :key="`act-reg-${idx}-${rIdx}`" class="q-mb-sm">
                        <div class="row q-col-gutter-sm items-center">
                          <div class="col-12 col-md-3">
                            <q-input v-model="register.name" label="Имя" dense standout="bg-dark" />
                          </div>
                          <div class="col-12 col-md-3">
                            <q-select v-model="register.register_type" :options="registerTypeOptions" emit-value map-options label="Тип" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-2">
                            <q-input v-model.number="register.address" type="number" label="Адрес" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-2">
                            <q-input v-model.number="register.length" type="number" label="Длина" dense standout="bg-dark" />
                          </div>
                          <div class="col-12 col-md-2 text-right">
                            <q-btn dense flat round icon="delete" color="negative" @click="removeRegister(act.registers, rIdx)" />
                          </div>
                          <div class="col-12 col-md-4">
                            <q-input v-model="register.description" label="Описание" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-4">
                            <q-input v-model="register.on_value" label="On value" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-4">
                            <q-input v-model="register.off_value" label="Off value" dense standout="bg-dark" />
                          </div>
                        </div>
                      </div>
                      <q-btn flat color="primary" icon="add" label="Регистр" @click="addRegister(act.registers)" />
                    </q-card-section>
                  </q-card>
                </div>
                <q-btn flat color="primary" icon="add" label="Добавить актуатор" @click="addFeature(moduleForm.actuators)" />
              </div>

              <div class="col-12 q-mt-md">
                <div class="text-subtitle2 text-white q-mb-sm">Сенсоры</div>
                <div v-for="(sensor, idx) in moduleForm.sensors" :key="`sensor-${idx}`" class="q-mb-sm">
                  <q-card flat bordered class="bg-dark-2">
                    <q-card-section>
                      <div class="row q-col-gutter-sm items-center q-mb-sm">
                        <div class="col-12 col-md-4">
                          <q-input v-model="sensor.slug" label="Имя сенсора" dense standout="bg-dark" />
                        </div>
                        <div class="col-12 col-md-4">
                          <q-input v-model="sensor.description" label="Описание" dense standout="bg-dark" />
                        </div>
                        <div class="col-12 col-md-4 text-right">
                          <q-btn dense flat round icon="delete" color="negative" @click="removeFeature(moduleForm.sensors, idx)" />
                        </div>
                      </div>
                      <div v-for="(register, rIdx) in sensor.registers" :key="`sensor-reg-${idx}-${rIdx}`" class="q-mb-sm">
                        <div class="row q-col-gutter-sm items-center">
                          <div class="col-12 col-md-3">
                            <q-input v-model="register.name" label="Имя" dense standout="bg-dark" />
                          </div>
                          <div class="col-12 col-md-3">
                            <q-select v-model="register.register_type" :options="registerTypeOptions" emit-value map-options label="Тип" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-2">
                            <q-input v-model.number="register.address" type="number" label="Адрес" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-2">
                            <q-input v-model.number="register.length" type="number" label="Длина" dense standout="bg-dark" />
                          </div>
                          <div class="col-12 col-md-2 text-right">
                            <q-btn dense flat round icon="delete" color="negative" @click="removeRegister(sensor.registers, rIdx)" />
                          </div>
                          <div class="col-12 col-md-4">
                            <q-input v-model="register.description" label="Описание" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-4">
                            <q-input v-model="register.data_type" label="Тип данных" dense standout="bg-dark" />
                          </div>
                          <div class="col-6 col-md-4">
                            <q-input v-model="register.transform" label="Преобразование" dense standout="bg-dark" />
                          </div>
                        </div>
                      </div>
                      <q-btn flat color="primary" icon="add" label="Регистр" @click="addRegister(sensor.registers)" />
                    </q-card-section>
                  </q-card>
                </div>
                <q-btn flat color="primary" icon="add" label="Добавить сенсор" @click="addFeature(moduleForm.sensors)" />
              </div>
            </div>

            <div class="row q-col-gutter-md q-mt-md">
              <div class="col-12 col-md-6">
                <q-btn type="submit" color="primary" label="Сохранить" :loading="moduleSaving" class="full-width" />
              </div>
              <div class="col-12 col-md-6">
                <q-btn flat color="grey-5" label="Отмена" class="full-width" @click="closeModuleDialog" />
              </div>
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import StatusCard from 'components/StatusCard.vue';
import { useAppStore } from 'stores/app-store';
import {
  useDeviceStore,
  type DeviceKind,
  type DeviceRecord,
  type DeviceUpdatePayload,
} from 'stores/device-store';
import {
  useModuleConfigStore,
  type ModuleConfig,
  type ModuleFeature,
  type ModuleRegister,
  type ModuleTypeConfig,
} from 'stores/module-config-store';
import { useWifiStore } from 'stores/wifi-store';
import { api } from 'boot/axios';

const store = useAppStore();
const deviceStore = useDeviceStore();
const moduleConfigStore = useModuleConfigStore();
const wifiStore = useWifiStore();
const {
  versions,
  systemMetrics,
  loadingVersions,
  loadingSystem,
  lastError,
} = storeToRefs(store);
const {
  loading: devicesLoading,
  saving: devicesSaving,
  error: devicesError,
  peripheralDevices,
  rs485Devices,
  portSuggestions,
  loadingPorts: portsLoading,
} = storeToRefs(deviceStore);
const {
  moduleTypes,
  modules,
  loading: moduleLoading,
  saving: moduleSaving,
  error: moduleError,
  restarting: moduleRestarting,
} = storeToRefs(moduleConfigStore);
const {
  networks: wifiNetworks,
  status: wifiStatus,
  loading: wifiLoading,
  connecting: wifiConnecting,
  error: wifiError,
} = storeToRefs(wifiStore);

const activeTab = ref('general');
const settingsSections = [
  {
    name: 'general',
    label: 'Основные',
    caption: 'Версии и мониторинг',
    icon: 'dashboard_customize',
  },
  {
    name: 'wifi',
    label: 'Wi-Fi',
    caption: 'Сети и пароль',
    icon: 'wifi',
  },
  {
    name: 'ports',
    label: 'UART порты',
    caption: 'Периферия и RS-485',
    icon: 'settings_input_component',
  },
  {
    name: 'scanner',
    label: 'Modbus сканер',
    caption: 'Поиск устройств',
    icon: 'radar',
  },
  {
    name: 'modules',
    label: 'Модули',
    caption: '.cfg на диске',
    icon: 'memory',
  },
];

const versionCards = computed(() => {
  const current = versions.value;
  return [
    {
      label: 'Backend',
      value: current?.backend ?? '—',
      caption: 'Python сервисы и API',
      icon: 'hub',
    },
    {
      label: 'Frontend',
      value: current?.frontend ?? '—',
      caption: 'Vue / Quasar панель',
      icon: 'monitor',
    },
    {
      label: 'Firmware',
      value: current?.firmware ?? '—',
      caption: 'UART периферии',
      icon: 'memory',
    },
  ];
});

const portTypeOptions = [
  {
    label: 'Периферийный контроллер',
    value: 'peripheral' as DeviceKind,
  },
  {
    label: 'RS-485 шлюз',
    value: 'rs485' as DeviceKind,
  },
];

const rs485DeviceOptions = computed(() =>
  rs485Devices.value.map((device) => ({
    label: `${device.name} (${device.port})`,
    value: device.id,
    baudrate: device.baudrate,
  })),
);
const moduleTypeSelectOptions = computed(() =>
  moduleTypes.value.map((type) => ({ label: type.name, value: type.slug })),
);
const registerTypeOptions = [
  { label: 'Coil (DO)', value: 'coil' },
  { label: 'Discrete input (DI)', value: 'discrete_input' },
  { label: 'Input register (AI)', value: 'input_register' },
  { label: 'Holding register (AO)', value: 'holding_register' },
];
const moduleConfigPath = '~/.agritroller/configs';

const wifiForm = reactive<{ ssid: string; password: string }>({
  ssid: '',
  password: '',
});
const showWifiPassword = ref(false);
const wifiConnectError = ref<string | null>(null);
const sortedWifiNetworks = computed(() =>
  [...wifiNetworks.value].sort((a, b) => (Number(b.signal) || 0) - (Number(a.signal) || 0)),
);
const wifiStatusLabel = computed(() => {
  const status = wifiStatus.value?.status || 'disconnected';
  if (status === 'connected') {
    return wifiStatus.value?.ssid ? `Подключено к ${wifiStatus.value.ssid}` : 'Подключено';
  }
  if (status === 'error') {
    return 'Ошибка Wi-Fi';
  }
  return 'Не подключено';
});
const wifiStatusColor = computed(() => {
  const status = wifiStatus.value?.status;
  if (status === 'connected') return 'positive';
  if (status === 'error') return 'negative';
  return 'warning';
});
const wifiStatusDetails = computed(() => {
  const current = wifiStatus.value;
  if (!current) {
    return 'Статус Wi-Fi пока не загружен';
  }
  const lastConnected = current.last_connected_at
    ? new Date(current.last_connected_at).toLocaleString()
    : '—';
  if (current.last_error) {
    return `Не удалось подключиться: ${current.last_error}`;
  }
  return `Сеть: ${current.ssid || '—'} · Последнее подключение: ${lastConnected}`;
});

interface ScanResult {
  address: number;
  register: number;
  value: number | string;
  raw: string;
}

interface ScanJob {
  id: string;
  status: string;
  progress: number;
  total: number;
  results: ScanResult[];
  error?: string | null;
  started_at?: number;
}

const portForm = reactive<{
  name: string;
  kind: DeviceKind;
  port: string;
  baudrate: number;
}>({
  name: '',
  kind: 'peripheral',
  port: '',
  baudrate: 115200,
});

const portFormError = ref<string | null>(null);
const editForm = reactive<{
  id: number | null;
  name: string;
  kind: DeviceKind;
  port: string;
  baudrate: number;
  enabled: boolean;
  mapping: Record<string, unknown> | null;
}>({
  id: null,
  name: '',
  kind: 'peripheral',
  port: '',
  baudrate: 115200,
  enabled: true,
  mapping: null,
});
const editFormError = ref<string | null>(null);
const isEditDialogOpen = ref(false);
const isDeleteDialogOpen = ref(false);
const deleteTarget = ref<DeviceRecord | null>(null);
const deleteError = ref<string | null>(null);
const filteredPortOptions = ref<string[]>([]);
const extraPortOptions = ref<string[]>([]);
const refreshingDevices = ref<Set<number>>(new Set());
const allPortOptions = computed(() => {
  const merged = [...portSuggestions.value, ...extraPortOptions.value];
  return Array.from(new Set(merged));
});

const scanForm = reactive({
  deviceId: null as number | null,
  baudrate: 9600,
  startAddress: 1,
  endAddress: 10,
  register: 0,
  count: 1,
  timeout: 0.2,
});
const scanJob = ref<ScanJob | null>(null);
const scanError = ref<string | null>(null);
const scanLoading = ref(false);
const scanProgress = computed(() => {
  if (!scanJob.value || !scanJob.value.total) return 0;
  return Math.min(1, Math.max(0, scanJob.value.progress / scanJob.value.total));
});
interface ScanResult {
  address: number;
  register: number;
  value: number | string;
  raw: string;
}

const scanResults = computed<ScanResult[]>(() =>
  Array.isArray(scanJob.value?.results) ? (scanJob.value?.results as ScanResult[]) : [],
);
let scanPollHandle: number | null = null;

const isModuleTypeDialogOpen = ref(false);
const isModuleDialogOpen = ref(false);
const moduleTypeDialogMode = ref<'create' | 'edit'>('create');
const moduleDialogMode = ref<'create' | 'edit'>('create');
const moduleFormError = ref<string | null>(null);

const moduleTypeForm = reactive<{
  slug: string;
  name: string;
  description: string;
  registers: ModuleRegister[];
}>({
  slug: '',
  name: '',
  description: '',
  registers: [],
});

const moduleForm = reactive<{
  slug: string;
  name: string;
  module_type: string | null;
  description: string;
  registers: ModuleRegister[];
  actuators: ModuleFeature[];
  sensors: ModuleFeature[];
}>({
  slug: '',
  name: '',
  module_type: null,
  description: '',
  registers: [],
  actuators: [],
  sensors: [],
});

watch(
  allPortOptions,
  (options) => {
    filteredPortOptions.value = options;
  },
  { immediate: true },
);

watch(
  moduleTypes,
  (types) => {
    const first = types && types.length ? types[0] : null;
    if (!moduleForm.module_type && first) {
      moduleForm.module_type = first.slug;
    }
  },
  { immediate: true },
);

const isRefreshing = computed(
  () => loadingVersions.value || loadingSystem.value,
);

const metrics = computed(() => systemMetrics.value);

const cpuUsage = computed(() => {
  if (!metrics.value) return '—';
  return `${metrics.value.cpu.percent.toFixed(1)}%`;
});

const cpuDetails = computed(() => {
  if (!metrics.value) return 'Нет данных';
  const load = metrics.value.cpu.load_average;
  const loadText = Array.isArray(load) ? load.map((n) => n.toFixed(2)).join(', ') : 'n/a';
  return `Средняя загрузка: ${loadText} · Ядер: ${metrics.value.cpu.cores}`;
});

const memoryUsage = computed(() => {
  if (!metrics.value) return '—';
  return `${formatBytes(metrics.value.memory.used_bytes)} / ${formatBytes(metrics.value.memory.total_bytes)}`;
});

const memoryDetails = computed(() => {
  if (!metrics.value) return 'Нет данных';
  return `Свободно: ${formatBytes(metrics.value.memory.available_bytes)} · ${metrics.value.memory.percent.toFixed(1)}%`;
});

const storageUsage = computed(() => {
  if (!metrics.value) return '—';
  return `${formatBytes(metrics.value.storage.used_bytes)} / ${formatBytes(metrics.value.storage.total_bytes)}`;
});

const storageDetails = computed(() => {
  if (!metrics.value) return 'Нет данных';
  return `Том: ${metrics.value.storage.mount} · Свободно ${formatBytes(metrics.value.storage.free_bytes)} (${metrics.value.storage.percent.toFixed(1)}%)`;
});

const dbSize = computed(() => {
  if (!metrics.value) return '—';
  return formatBytes(metrics.value.database.size_bytes);
});

const dbPath = computed(() => metrics.value?.database.path ?? 'path unavailable');

async function refresh() {
  await store.loadSettingsData();
}

async function refreshWifiNetworks() {
  wifiConnectError.value = null;
  await wifiStore.fetchNetworks();
}

async function refreshWifiStatus() {
  wifiConnectError.value = null;
  await wifiStore.fetchStatus();
  if (wifiStatus.value?.ssid) {
    wifiForm.ssid = wifiStatus.value.ssid;
  }
}

function selectWifiNetwork(ssid: string) {
  wifiForm.ssid = ssid;
  wifiConnectError.value = null;
}

async function submitWifiConnect() {
  wifiConnectError.value = null;
  if (!wifiForm.ssid.trim()) {
    wifiConnectError.value = 'Выберите сеть или введите SSID';
    return;
  }
  try {
    const payload: { ssid: string; password?: string } = {
      ssid: wifiForm.ssid.trim(),
    };
    if (wifiForm.password) {
      payload.password = wifiForm.password;
    }
    await wifiStore.connect(payload);
    await Promise.all([wifiStore.fetchStatus(), wifiStore.fetchNetworks()]);
    wifiForm.password = '';
  } catch {
    wifiConnectError.value = wifiError.value ?? 'Не удалось подключиться к сети';
  }
}

function resetPortForm() {
  portForm.name = '';
  portForm.kind = 'peripheral';
  portForm.port = '';
  portForm.baudrate = 115200;
}

function resetEditForm() {
  editForm.id = null;
  editForm.name = '';
  editForm.kind = 'peripheral';
  editForm.port = '';
  editForm.baudrate = 115200;
  editForm.enabled = true;
  editFormError.value = null;
  editForm.mapping = null;
}

async function submitPort() {
  portFormError.value = null;
  if (!portForm.name.trim() || !portForm.port.trim()) {
    portFormError.value = 'Укажите название и путь к порту';
    return;
  }
  try {
    const payload = {
      kind: portForm.kind,
      name: portForm.name.trim(),
      port: portForm.port.trim(),
      baudrate: Math.max(300, Number(portForm.baudrate) || 0),
    } as const;
    await deviceStore.createDevice(payload);
    resetPortForm();
  } catch {
    portFormError.value = devicesError.value ?? 'Не удалось сохранить порт';
  }
}

function openEditDialog(device: DeviceRecord) {
  editForm.id = device.id;
  editForm.name = device.name;
  editForm.kind = device.kind;
  editForm.port = device.port;
  editForm.baudrate = device.baudrate;
  editForm.enabled = device.enabled;
  editForm.mapping = device.mapping || null;
  editFormError.value = null;
  isEditDialogOpen.value = true;
}

function closeEditDialog() {
  isEditDialogOpen.value = false;
  resetEditForm();
}

async function submitEditForm() {
  editFormError.value = null;
  if (!editForm.id) {
    editFormError.value = 'Не выбран порт для редактирования';
    return;
  }
  if (!editForm.name.trim() || !editForm.port.trim()) {
    editFormError.value = 'Заполните название и путь к порту';
    return;
  }
  try {
    const payload: DeviceUpdatePayload = {
      name: editForm.name.trim(),
      kind: editForm.kind,
      port: editForm.port.trim(),
      baudrate: Math.max(300, Number(editForm.baudrate) || 0),
      enabled: editForm.enabled,
    };
    if (editForm.mapping) {
      payload.mapping = editForm.mapping;
    }
    await deviceStore.updateDevice(editForm.id, payload);
    closeEditDialog();
  } catch {
    editFormError.value = devicesError.value ?? 'Не удалось сохранить изменения';
  }
}

function requestDelete(device: DeviceRecord) {
  deleteTarget.value = device;
  deleteError.value = null;
  isDeleteDialogOpen.value = true;
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value = false;
  deleteTarget.value = null;
  deleteError.value = null;
}

async function confirmDelete() {
  if (!deleteTarget.value) {
    return;
  }
  deleteError.value = null;
  try {
    await deviceStore.deleteDevice(deleteTarget.value.id);
    closeDeleteDialog();
  } catch {
    deleteError.value = devicesError.value ?? 'Не удалось удалить устройство';
  }
}

function setTab(tabName: string) {
  activeTab.value = tabName;
}

function filterPortOptions(val: string, update: (callback: () => void) => void) {
  update(() => {
    if (!val) {
      filteredPortOptions.value = allPortOptions.value;
      return;
    }
    const needle = val.toLowerCase();
    filteredPortOptions.value = allPortOptions.value.filter((option: string) =>
      option.toLowerCase().includes(needle),
    );
  });
}

function handlePortInput(value: string) {
  portForm.port = value;
}

function handleEditPortInput(value: string) {
  editForm.port = value;
}

function handlePortNewValue(
  value: string,
  done: (value?: string, mode?: 'add' | 'add-unique') => void,
) {
  const trimmed = value.trim();
  if (!trimmed) {
    done();
    return;
  }
  if (
    !portSuggestions.value.includes(trimmed) &&
    !extraPortOptions.value.includes(trimmed)
  ) {
    extraPortOptions.value = [...extraPortOptions.value, trimmed];
  }
  portForm.port = trimmed;
  if (isEditDialogOpen.value) {
    editForm.port = trimmed;
  }
  done(trimmed, 'add-unique');
}

function formatBytes(value: number) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let val = value;
  let idx = 0;
  while (val >= 1024 && idx < units.length - 1) {
    val /= 1024;
    idx += 1;
  }
  return `${val.toFixed(val >= 10 ? 0 : 1)} ${units[idx]}`;
}

function extractErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response: { data?: { detail?: string; message?: string } } }).response;
    const detail = response?.data?.detail ?? response?.data?.message;
    if (detail) {
      return detail;
    }
  }
  return 'Произошла ошибка';
}

function setRefreshing(deviceId: number, value: boolean) {
  const clone = new Set(refreshingDevices.value);
  if (value) {
    clone.add(deviceId);
  } else {
    clone.delete(deviceId);
  }
  refreshingDevices.value = clone;
}

function isDeviceRefreshing(deviceId: number) {
  return refreshingDevices.value.has(deviceId);
}

async function refreshDeviceStatus(deviceId: number) {
  if (isDeviceRefreshing(deviceId)) {
    return;
  }
  setRefreshing(deviceId, true);
  try {
    await deviceStore.refreshDeviceStatus(deviceId);
  } catch {
    // error surfaced via banner
  } finally {
    setRefreshing(deviceId, false);
  }
}

async function runScan() {
  scanError.value = null;
  const selectedDevice = rs485Devices.value.find((device) => device.id === scanForm.deviceId);
  if (!selectedDevice) {
    scanError.value = 'Выберите RS-485 устройство';
    return;
  }
  if (scanForm.startAddress > scanForm.endAddress) {
    scanError.value = 'Начальный адрес не может быть больше конечного';
    return;
  }
  scanLoading.value = true;
  try {
    const response = await api.post<ScanJob>('/rs485/scan', {
      device_id: selectedDevice.id,
      baudrate: Math.max(1200, Number(scanForm.baudrate) || selectedDevice.baudrate),
      start_address: scanForm.startAddress,
      end_address: scanForm.endAddress,
      register: Math.max(0, Number(scanForm.register) || 0),
      count: Math.max(1, Number(scanForm.count) || 1),
      timeout: Math.max(0.05, Number(scanForm.timeout) || 0.2),
    });
    scanJob.value = response.data;
    startScanPolling(response.data.id);
  } catch (error) {
    scanError.value = extractErrorMessage(error);
  } finally {
    scanLoading.value = false;
  }
}

function startScanPolling(jobId: string) {
  stopScanPolling();
  scanPollHandle = window.setInterval(() => {
    void (async () => {
      try {
        const response = await api.get<ScanJob>(`/rs485/scan/${jobId}`);
        scanJob.value = response.data;
        if (response.data.status !== 'running') {
          stopScanPolling();
        }
      } catch (error) {
        scanError.value = extractErrorMessage(error);
        stopScanPolling();
      }
    })();
  }, 800);
}

function stopScanPolling() {
  if (scanPollHandle !== null) {
    window.clearInterval(scanPollHandle);
    scanPollHandle = null;
  }
}

function resetScan() {
  scanJob.value = null;
  scanError.value = null;
  stopScanPolling();
}

async function createDeviceFromResult(result: ScanResult) {
  const selected = rs485Devices.value.find((device) => device.id === scanForm.deviceId);
  if (!selected) {
    scanError.value = 'Выберите RS-485 устройство';
    return;
  }
  try {
    await deviceStore.createDevice({
      kind: 'rs485',
      name: `Modbus ${result.address}`,
      port: selected.port,
      baudrate: Math.max(1200, Number(scanForm.baudrate) || selected.baudrate),
      metadata: {
        modbus_address: result.address,
        register: result.register,
        raw: result.raw,
      },
    });
  } catch (error) {
    scanError.value = extractErrorMessage(error);
  }
}

function createEmptyRegister(): ModuleRegister {
  return {
    name: '',
    register_type: 'coil',
    address: 0,
    length: 1,
    description: '',
    data_type: '',
    transform: '',
    on_value: null,
    off_value: null,
  };
}

function addRegister(target: ModuleRegister[]) {
  target.push({ ...createEmptyRegister() });
}

function removeRegister(target: ModuleRegister[], index: number) {
  if (index >= 0 && index < target.length) {
    target.splice(index, 1);
  }
}

function addFeature(target: ModuleFeature[]) {
  target.push({ slug: '', registers: [{ ...createEmptyRegister() }] });
}

function removeFeature(target: ModuleFeature[], index: number) {
  if (index >= 0 && index < target.length) {
    target.splice(index, 1);
  }
}

function resetModuleTypeForm() {
  moduleTypeForm.slug = '';
  moduleTypeForm.name = '';
  moduleTypeForm.description = '';
  moduleTypeForm.registers = [{ ...createEmptyRegister() }];
  moduleFormError.value = null;
}

function resetModuleForm() {
  moduleForm.slug = '';
  moduleForm.name = '';
  moduleForm.module_type = null;
  moduleForm.description = '';
  moduleForm.registers = [{ ...createEmptyRegister() }];
  moduleForm.actuators = [];
  moduleForm.sensors = [];
  moduleFormError.value = null;
}

function openModuleTypeDialog(existing?: ModuleTypeConfig) {
  moduleTypeDialogMode.value = existing ? 'edit' : 'create';
  if (existing) {
    moduleTypeForm.slug = existing.slug;
    moduleTypeForm.name = existing.name;
    moduleTypeForm.description = existing.description || '';
    moduleTypeForm.registers = (existing.registers || []).map((reg) => ({ ...reg }));
  } else {
    resetModuleTypeForm();
  }
  isModuleTypeDialogOpen.value = true;
}

function closeModuleTypeDialog() {
  isModuleTypeDialogOpen.value = false;
  resetModuleTypeForm();
}

function normalizeRegister(register: ModuleRegister): ModuleRegister {
  return {
    ...register,
    address: Number(register.address) || 0,
    length: Math.max(1, Number(register.length) || 1),
    description: register.description ?? '',
    data_type: register.data_type ?? '',
    transform: register.transform ?? '',
  };
}

async function submitModuleType() {
  moduleFormError.value = null;
  if (!moduleTypeForm.slug.trim() || !moduleTypeForm.name.trim()) {
    moduleFormError.value = 'Укажите slug и имя типа модуля';
    return;
  }
  if (!moduleTypeForm.registers.length) {
    moduleFormError.value = 'Добавьте хотя бы один регистр';
    return;
  }
  const payload: ModuleTypeConfig = {
    slug: moduleTypeForm.slug.trim(),
    name: moduleTypeForm.name.trim(),
    description: moduleTypeForm.description || '',
    registers: moduleTypeForm.registers.map((reg) => normalizeRegister(reg)),
  };
  try {
    await moduleConfigStore.saveModuleType(payload, moduleTypeDialogMode.value === 'edit');
    closeModuleTypeDialog();
  } catch (error) {
    moduleFormError.value = extractErrorMessage(error);
  }
}

function openModuleDialog(existing?: ModuleConfig) {
  moduleDialogMode.value = existing ? 'edit' : 'create';
  if (existing) {
    moduleForm.slug = existing.slug;
    moduleForm.name = existing.name;
    moduleForm.module_type = existing.module_type || null;
    moduleForm.description = (existing.meta?.description as string) || existing.description || '';
    moduleForm.registers = (existing.registers || []).map((reg) => ({ ...reg }));
    moduleForm.actuators = (existing.actuators || []).map((act) => ({
      ...act,
      registers: (act.registers || []).map((reg) => ({ ...reg })),
    }));
    moduleForm.sensors = (existing.sensors || []).map((sensor) => ({
      ...sensor,
      registers: (sensor.registers || []).map((reg) => ({ ...reg })),
    }));
  } else {
    resetModuleForm();
  }
  isModuleDialogOpen.value = true;
}

function closeModuleDialog() {
  isModuleDialogOpen.value = false;
  resetModuleForm();
}

async function submitModule() {
  moduleFormError.value = null;
  if (!moduleForm.slug.trim() || !moduleForm.name.trim()) {
    moduleFormError.value = 'Укажите slug и имя модуля';
    return;
  }
  const payload: ModuleConfig = {
    slug: moduleForm.slug.trim(),
    name: moduleForm.name.trim(),
    module_type: moduleForm.module_type ?? null,
    description: moduleForm.description || null,
    registers: moduleForm.registers.map((reg) => normalizeRegister(reg)),
    actuators: moduleForm.actuators.map((act) => ({
      ...act,
      registers: act.registers.map((reg) => normalizeRegister(reg)),
    })),
    sensors: moduleForm.sensors.map((sensor) => ({
      ...sensor,
      registers: sensor.registers.map((reg) => normalizeRegister(reg)),
    })),
    type_registers: [],
  };
  try {
    await moduleConfigStore.saveModule(payload, moduleDialogMode.value === 'edit');
    closeModuleDialog();
  } catch (error) {
    moduleFormError.value = extractErrorMessage(error);
  }
}

async function deleteModuleType(slug: string) {
  try {
    await moduleConfigStore.deleteModuleType(slug);
  } catch (error) {
    moduleFormError.value = extractErrorMessage(error);
  }
}

async function deleteModule(slug: string) {
  try {
    await moduleConfigStore.deleteModule(slug);
  } catch (error) {
    moduleFormError.value = extractErrorMessage(error);
  }
}

async function refreshModuleConfigs() {
  moduleFormError.value = null;
  try {
    await moduleConfigStore.refreshAll();
  } catch (error) {
    moduleFormError.value = extractErrorMessage(error);
  }
}

async function requestRestart() {
  moduleFormError.value = null;
  try {
    await moduleConfigStore.requestRestart();
  } catch (error) {
    moduleFormError.value = extractErrorMessage(error);
  }
}

function statusColor(status?: string) {
  switch (status) {
    case 'available':
      return 'positive';
    case 'busy':
      return 'warning';
    case 'missing':
      return 'negative';
    default:
      return 'grey-7';
  }
}

function statusLabel(status?: string) {
  switch (status) {
    case 'available':
      return 'Доступен';
    case 'busy':
      return 'Занят';
    case 'missing':
      return 'Отсутствует';
    default:
      return 'Неизвестно';
  }
}

function formatStatusTimestamp(value?: string | null) {
  if (!value) {
    return 'не проверялось';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

onMounted(async () => {
  await Promise.all([
    refresh(),
    deviceStore.fetchDevices(),
    deviceStore.fetchPortSuggestions(),
    moduleConfigStore.refreshAll(),
    wifiStore.fetchStatus(),
    wifiStore.fetchNetworks(),
  ]);
});

onBeforeUnmount(() => {
  stopScanPolling();
});
</script>

<style scoped lang="scss">
.settings-page {
  min-height: 100vh;
  background: radial-gradient(circle at top, rgba(14, 165, 233, 0.08), transparent 45%),
    #0b1120;
}

.settings-container {
  max-width: 1280px;
  margin: 0 auto;
}

.settings-layout {
  margin-top: 32px;
}

.event-status {
  display: flex;
  flex-direction: column;
}

.main-panels {
  background: transparent;
}

.main-panels :deep(.q-tab-panel) {
  padding-left: 0;
  padding-right: 0;
}

.ports-subtitle {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}

.sidebar-card {
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.05);
  position: sticky;
  top: 96px;
}

.sidebar-nav .q-item {
  transition: background-color 0.2s;
}

.sidebar-nav .q-item:hover {
  background-color: rgba(148, 163, 184, 0.1);
}

.sidebar-active {
  background-color: rgba(14, 165, 233, 0.15);
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #f8fafc;
}

.section-subtitle {
  color: #94a3b8;
}

.dashboard-card {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.edit-dialog-card,
.delete-dialog-card {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  width: 100%;
}

.edit-dialog-card {
  max-width: 640px;
}

.delete-dialog-card {
  max-width: 420px;
}

.metric-label {
  font-size: 14px;
  color: #94a3b8;
  text-transform: uppercase;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
  color: #f8fafc;
}
</style>
