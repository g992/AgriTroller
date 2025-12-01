Options
You can customize the Keyboard by passing the following options to it. Click on any option to see more details and examples.

Layout & Display
Option	Description
layout	Modify the keyboard layout.
layoutName	Specifies which layout should be used.
display	Replaces variable buttons (such as {bksp}) with a human-friendly name (e.g.: backspace).
mergeDisplay	By default, when you set the display property, you replace the default one. This setting merges them instead.
excludeFromLayout	Exclude buttons from layout.
Styling & Theming
Option	Description
theme	A prop to add your own css classes to the keyboard wrapper. You can add multiple classes separated by a space.
buttonTheme	A prop to add your own css classes to one or several buttons.
buttonAttributes	A prop to add your own attributes to one or several buttons.
useButtonTag	Render buttons as a button element instead of a div element.
baseClass	Set a custom base class for the keyboard wrapper.
Input Handling
Option	Description
inputName	Allows you to use a single simple-keyboard instance for several inputs.
maxLength	Restrains all of simple-keyboard inputs to a certain length. This should be used in addition to the input element's maxlength attribute.
inputPattern	Restrains input(s) change to the defined regular expression pattern.
newLineOnEnter	Specifies whether clicking the "ENTER" button will input a newline (\n) or not.
tabCharOnTab	Specifies whether clicking the "TAB" button will input a tab character (\t) or not.
syncInstanceInputs	When set to true, this option synchronizes the internal input of every simple-keyboard instance.
Caret & Text Positioning
Option	Description
disableCaretPositioning	A prop to ensure characters are always be added/removed at the end of the string.
updateCaretOnSelectionChange	Updates caret when selectionchange event is fired.
Mouse & Touch Events
Option	Description
useMouseEvents	Opt out of PointerEvents handling, falling back to the prior mouse event logic.
useTouchEvents	Instructs simple-keyboard to use touch events instead of click events.
autoUseTouchEvents	Enable useTouchEvents automatically when touch device is detected.
clickOnMouseDown	When useMouseEvents is enabled, this option allows you to trigger a button click event on mousedown.
preventMouseDownDefault	Calling preventDefault for the mousedown events keeps the focus on the input.
preventMouseUpDefault	Calling preventDefault for the mouseup events.
stopMouseDownPropagation	Stops pointer down events on simple-keyboard buttons from bubbling to parent elements.
stopMouseUpPropagation	Stops pointer up events on simple-keyboard buttons from bubbling to parent elements.
disableButtonHold	Disable button hold action.
Physical Keyboard Integration
Option	Description
physicalKeyboardHighlight	Enable highlighting of keys pressed on physical keyboard.
physicalKeyboardHighlightPress	Calls handler for a button highlighted by physicalKeyboardHighlight. In other words, this calls keyboard.handleButtonClicked(buttonName) on the highlighted button.
physicalKeyboardHighlightPressUseClick	Trigger click on a button's element when using physicalKeyboardHighlightPress. In other words, this calls button.click() on the highlighted button.
physicalKeyboardHighlightPressUsePointerEvents	Whether physicalKeyboardHighlightPress should use pointer events to trigger buttons.
physicalKeyboardHighlightPreventDefault	Whether physicalKeyboardHighlight should use preventDefault to disable default browser actions.
physicalKeyboardHighlightTextColor	Define the text color that the physical keyboard highlighted key should have.
physicalKeyboardHighlightBgColor	Define the background color that the physical keyboard highlighted key should have.
Layout Candidates (IME Support)
Option	Description
enableLayoutCandidates	Enable input method editor candidate list support.
layoutCandidates	Character suggestions to be shown on certain key presses.
layoutCandidatesPageSize	Determines size of layout candidate list.
layoutCandidatesCaseSensitiveMatch	Determines whether layout candidate match should be case sensitive.
disableCandidateNormalization	Disables the automatic normalization for selected layout candidates.
enableLayoutCandidatesKeyPress	Enables onKeyPress triggering for layoutCandidate items.
Localization
Option	Description
rtl	Adds unicode right-to-left control characters to input return values.
Event Callbacks
Option	Description
onKeyPress	Retrieves the pressed key.
onChange	Retrieves the current input.
onChangeAll	Retrieves all inputs.
onKeyReleased	Retrieves the released key.
onRender	Executes the callback function every time simple-keyboard is rendered (e.g: when you change layouts).
onInit	Executes the callback function once simple-keyboard is rendered for the first time (on initialization).
beforeInputUpdate	Executes the callback function before an input is about to be updated.
Debug & Development
Option	Description
debug	Runs a console.log every time a key is pressed. Displays the buttons pressed and the current input.
