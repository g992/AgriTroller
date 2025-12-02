<template>
  <div class="kiosk-keyboard-field">
    <q-input
      :model-value="modelValue"
      :label="label"
      :hint="hint"
      :counter="counter"
      :maxlength="maxlength"
      :disable="disable"
      :input-attr="inputAttrs"
      :type="type"
      standout="bg-dark"
      stack-label
      dense
      readonly
      autocomplete="off"
      @focus="openDialog"
      @click="openDialog"
    />

    <q-dialog v-model="dialog" persistent>
      <q-card class="kiosk-card kiosk-keyboard-dialog">
        <q-card-section class="row items-center justify-between q-gutter-sm">
          <div>
            <div class="text-h6 text-white">{{ label }}</div>
            <div v-if="hint" class="text-caption text-grey-5">{{ hint }}</div>
          </div>
          <q-btn dense flat round icon="close" color="grey-5" @click="closeDialog" />
        </q-card-section>
        <q-card-section class="q-gutter-md kiosk-keyboard-dialog-body">
        <q-input
          v-model="dialogValue"
          :type="type"
          :maxlength="maxlength"
          :counter="counter"
          :input-attr="inputAttrs"
          standout="bg-dark"
          stack-label
          dense
          autofocus
          @keyup.enter.prevent="applyValue"
        />
        <div v-if="suggestions?.length" class="row q-col-gutter-sm">
          <div class="col-12 text-caption text-grey-5">Быстрый выбор</div>
          <div class="col-12">
            <div class="row q-col-gutter-sm">
              <div v-for="option in suggestions" :key="option" class="col-auto">
                <q-chip clickable color="grey-8" text-color="white" outline @click="selectSuggestion(option)">
                  {{ option }}
                </q-chip>
              </div>
            </div>
          </div>
        </div>
        <KioskKeyboard
          v-model="dialogValue"
          :layout="layout"
          :title="keyboardTitle"
          :hint="hint"
          submit-label="Готово"
          @submit="applyValue"
          @close="closeDialog"
        />
          <div class="row justify-end q-gutter-sm">
            <q-btn flat color="white" label="Отмена" @click="closeDialog" />
            <q-btn color="primary" label="Готово" @click="applyValue" />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, type PropType } from 'vue';
import type { QInputProps } from 'quasar';
import KioskKeyboard from 'components/KioskKeyboard.vue';

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  label: {
    type: String,
    default: 'Поле ввода',
  },
  hint: {
    type: String,
    default: '',
  },
  layout: {
    type: String as PropType<'alphanumeric' | 'numeric'>,
    default: 'alphanumeric',
  },
  type: {
    type: String as PropType<QInputProps['type']>,
    default: 'text',
  },
  maxlength: {
    type: Number,
    default: undefined,
  },
  counter: {
    type: Boolean,
    default: false,
  },
  disable: {
    type: Boolean,
    default: false,
  },
  inputmode: {
    type: String,
    default: undefined,
  },
  suggestions: {
    type: Array as () => string[],
    default: () => [],
  },
});

const emit = defineEmits(['update:modelValue']);

const dialog = ref(false);
const dialogValue = ref(props.modelValue ?? '');

const inputAttrs = computed(() =>
  props.inputmode ? { inputmode: props.inputmode } : undefined,
);

const keyboardTitle = computed(() => props.label || 'Клавиатура');

watch(
  () => props.modelValue,
  (value) => {
    if (!dialog.value) {
      dialogValue.value = value ?? '';
    }
  },
);

function openDialog() {
  if (props.disable) return;
  dialogValue.value = props.modelValue ?? '';
  dialog.value = true;
}

function closeDialog() {
  dialog.value = false;
}

function applyValue() {
  emit('update:modelValue', dialogValue.value ?? '');
  closeDialog();
}

function selectSuggestion(value: string) {
  dialogValue.value = value;
  applyValue();
}
</script>

<style scoped lang="scss">
.kiosk-keyboard-field {
  width: 100%;
}

.kiosk-keyboard-dialog {
  width: 100%;
  max-width: 900px;
}

.kiosk-keyboard-dialog-body {
  padding-left: 16px;
  padding-right: 16px;
}
</style>
