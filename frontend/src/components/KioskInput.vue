<template>
  <div class="kiosk-input">
    <q-input
      v-model="localValue"
      :label="label"
      :placeholder="placeholder"
      :hint="hint"
      standout="bg-dark"
      stack-label
      rounded
      readonly
      :disable="disable"
      :clearable="clearable"
      class="kiosk-input__field"
      input-class="kiosk-input__text"
      :input-style="inputStyle"
      @focus="openKeyboard"
      @click="openKeyboard"
      @clear="clearValue"
    >
      <template #append>
        <q-icon name="keyboard" class="cursor-pointer" @click.stop="toggleKeyboard" />
      </template>
    </q-input>

    <q-dialog
      v-model="isKeyboardOpen"
      position="bottom"
      :maximized="true"
      transition-show="slide-up"
      transition-hide="slide-down"
      class="kiosk-input__dialog"
      @hide="emitBlur"
    >
      <KioskKeyboard
        v-model="localValue"
        :layout="keyboardLayout"
        :title="keyboardTitle || label || 'Ввод'"
        :hint="keyboardHint"
        :submit-label="submitLabel"
        :show-close="true"
        :max-length="maxLength"
        @submit="handleSubmit"
        @close="closeKeyboard"
        @input="handleKeyboardInput"
      />
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, type PropType } from 'vue';
import KioskKeyboard from './KioskKeyboard.vue';

type KeyboardLayout = 'alphanumeric' | 'numeric';

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: '',
  },
  label: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '',
  },
  hint: {
    type: String,
    default: '',
  },
  keyboardLayout: {
    type: String as PropType<KeyboardLayout>,
    default: 'alphanumeric',
  },
  keyboardTitle: {
    type: String,
    default: '',
  },
  keyboardHint: {
    type: String,
    default: 'Нажмите на клавиши ниже для ввода',
  },
  submitLabel: {
    type: String,
    default: 'Готово',
  },
  disable: {
    type: Boolean,
    default: false,
  },
  clearable: {
    type: Boolean,
    default: true,
  },
  maxLength: {
    type: Number,
    default: undefined,
  },
  autoCloseOnSubmit: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(['update:modelValue', 'submit', 'focus', 'blur']);

const isKeyboardOpen = ref(false);
const localValue = ref(stringifyValue(props.modelValue));
const inputStyle: Record<string, string> = {
  paddingTop: '22px',
  paddingBottom: '12px',
  fontSize: '20px',
};

watch(
  () => props.modelValue,
  (value) => {
    if (stringifyValue(value) !== localValue.value) {
      localValue.value = stringifyValue(value);
    }
  },
);

function stringifyValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value);
}

function openKeyboard() {
  if (props.disable) return;
  isKeyboardOpen.value = true;
  emit('focus');
}

function toggleKeyboard() {
  isKeyboardOpen.value = !isKeyboardOpen.value;
  if (isKeyboardOpen.value) {
    emit('focus');
  }
}

function closeKeyboard() {
  isKeyboardOpen.value = false;
}

function emitBlur() {
  emit('blur');
}

function handleKeyboardInput(value: string) {
  localValue.value = value;
  emit('update:modelValue', value);
}

function handleSubmit() {
  emit('submit', localValue.value);
  emit('update:modelValue', localValue.value);
  if (props.autoCloseOnSubmit) {
    closeKeyboard();
  }
}

function clearValue() {
  localValue.value = '';
  emit('update:modelValue', '');
}

</script>

<style scoped lang="scss">
.kiosk-input__field {
  font-size: 20px;
}

.kiosk-input__text {
  font-size: 20px;
  letter-spacing: 0.5px;
}

.kiosk-input__dialog {
  background: transparent;
  padding: 12px;
}

:deep(.kiosk-input__field .q-field__control) {
  min-height: 68px;
}

:deep(.kiosk-input__field .q-field__label) {
  top: 8px;
  font-size: 16px;
}

@media (max-width: 640px) {
  .kiosk-input__field,
  .kiosk-input__text {
    font-size: 18px;
  }
}
</style>
