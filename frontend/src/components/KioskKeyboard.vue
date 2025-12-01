<template>
  <div class="kiosk-keyboard">
    <div class="keyboard-header">
      <div>
        <div class="text-h6 text-white text-weight-bold">{{ title }}</div>
        <div v-if="hint" class="text-caption text-grey-5">{{ hint }}</div>
      </div>
      <div class="row items-center q-gutter-sm">
        <q-btn
          v-if="showClose"
          dense
          flat
          round
          color="grey-4"
          icon="close"
          aria-label="Закрыть клавиатуру"
          @click="emitClose"
        />
        <q-btn
          v-if="showSubmitButton"
          color="primary"
          text-color="black"
          unelevated
          size="md"
          icon="check"
          :label="submitLabel"
          @click="emitSubmit"
        />
      </div>
    </div>

    <div class="keyboard-wrapper">
      <div ref="keyboardRef" class="simple-keyboard kiosk-simple-keyboard" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type PropType } from 'vue';
import Keyboard from 'simple-keyboard';
import 'simple-keyboard/build/css/index.css';

type KeyboardLayout = 'alphanumeric' | 'numeric';
type AlphaLayoutName = 'default' | 'shift' | 'alt';

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  layout: {
    type: String as PropType<KeyboardLayout>,
    default: 'alphanumeric',
  },
  title: {
    type: String,
    default: 'Клавиатура',
  },
  hint: {
    type: String,
    default: '',
  },
  submitLabel: {
    type: String,
    default: 'Готово',
  },
  showClose: {
    type: Boolean,
    default: true,
  },
  showSubmitButton: {
    type: Boolean,
    default: true,
  },
  maxLength: {
    type: Number as PropType<number | undefined>,
    default: undefined,
  },
});

const emit = defineEmits(['update:modelValue', 'submit', 'close', 'input']);

const keyboardRef = ref<HTMLElement | null>(null);
const keyboard = ref<Keyboard | null>(null);
const alphaLayoutName = ref<AlphaLayoutName>('default');

const display = computed(() => ({
  '{bksp}': '⌫',
  '{enter}': props.submitLabel || 'Готово',
  '{space}': 'space',
  '{shift}': '⇧',
  '{shiftactivated}': '⇧',
  '{alt}': '123',
  '{default}': 'ABC',
  // '{downkeyboard}': '🞃',
}));

const iosLayout = {
  default: [
    'q w e r t y u i o p {bksp}',
    'a s d f g h j k l {enter}',
    '{shift} z x c v b n m , . {shift}',
    '{alt} {space}',
  ],
  shift: [
    'Q W E R T Y U I O P {bksp}',
    'A S D F G H J K L {enter}',
    '{shiftactivated} Z X C V B N M , . {shiftactivated}',
    '{alt} {space}',
  ],
  alt: [
    '1 2 3 4 5 6 7 8 9 0 {bksp}',
    "@ # $ & * ( ) ' \" {enter}",
    '{shift} % - + = / ; : ! ? {shift}',
    '{default} {space}',
  ],
};

const numericLayout = {
  default: ['1 2 3', '4 5 6', '7 8 9', '0 . {bksp}', '{enter} {space}'],
};

const currentLayout = computed(() => {
  if (props.layout === 'numeric') {
    return { layout: numericLayout, layoutName: 'default' as const };
  }
  return { layout: iosLayout, layoutName: alphaLayoutName.value };
});

onMounted(() => {
  if (!keyboardRef.value) {
    return;
  }
  keyboard.value = new Keyboard(keyboardRef.value, {
    layout: currentLayout.value.layout,
    layoutName: currentLayout.value.layoutName,
    display: display.value,
    theme: 'hg-theme-default hg-theme-ios kiosk-theme',
    preventMouseDownDefault: true,
    preventMouseUpDefault: true,
    maxLength: props.maxLength,
    newLineOnEnter: false,
    tabCharOnTab: false,
    onChange: handleChange,
    onKeyPress: handleKeyPress,
  });
  // set initial value
  keyboard.value.setInput(props.modelValue ?? '');
});

onBeforeUnmount(() => {
  keyboard.value?.destroy();
});

watch(
  () => props.modelValue,
  (value) => {
    if (!keyboard.value) return;
    const next = value ?? '';
    if (keyboard.value.getInput() !== next) {
      keyboard.value.setInput(next);
    }
  },
);

watch([() => props.layout, alphaLayoutName, display], () => {
  if (!keyboard.value) return;
  keyboard.value.setOptions({
    layout: currentLayout.value.layout,
    layoutName: currentLayout.value.layoutName,
    display: display.value,
    maxLength: props.maxLength,
  });
});

function handleChange(input: string) {
  emit('update:modelValue', input);
  emit('input', input);
}

function handleKeyPress(button: string) {
  if (button === '{enter}') {
    emitSubmit();
    return;
  }
  if (button === '{shift}' || button === '{shiftactivated}') {
    toggleShift();
    return;
  }
  if (button === '{alt}' || button === '{default}') {
    toggleAlt(button);
    return;
  }
  if (button === '{downkeyboard}') {
    emitClose();
    return;
  }
}

function emitSubmit() {
  emit('submit');
}

function emitClose() {
  emit('close');
}

function toggleShift() {
  alphaLayoutName.value = alphaLayoutName.value === 'shift' ? 'default' : 'shift';
}

function toggleAlt(button: string) {
  if (button === '{default}') {
    alphaLayoutName.value = 'default';
    return;
  }
  alphaLayoutName.value = alphaLayoutName.value === 'alt' ? 'default' : 'alt';
}
</script>

<style scoped lang="scss">
@import 'simple-keyboard/build/css/index.css';

.kiosk-keyboard {
  width: 100%;
  background: #0b1221;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 12px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
}

.keyboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
}

.keyboard-wrapper {
  padding: 4px;
}

.kiosk-simple-keyboard {
  background: transparent;
}

:deep(.hg-theme-default) {
  background-color: transparent;
  box-shadow: none;
  padding: 0;
}

:deep(.hg-theme-default .hg-button) {
  border-radius: 12px;
  min-height: 52px;
  font-size: 16px;
  font-weight: 700;
  background: #0f172a;
  color: #f8fafc;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

:deep(.hg-theme-default .hg-button-space) {
  flex: 3;
}

:deep(.hg-theme-default .hg-button-alt),
:deep(.hg-theme-default .hg-button-default) {
  flex: 1;
  min-width: 72px;
}

:deep(.hg-theme-default .hg-button:hover) {
  background: #111c34;
}

:deep(.hg-theme-default .hg-button.hg-functionBtn) {
  background: #1f2937;
  color: #e2e8f0;
}

@media (max-width: 640px) {
  .hg-theme-default .hg-button {
    min-height: 48px;
    font-size: 15px;
  }
}
</style>
