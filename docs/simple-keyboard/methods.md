Methods
simple-keyboard has a few methods you can use to further control its behavior. To access these functions, you need the instance of the keyboard component, like so:

const keyboard = new Keyboard({
  ...
});

// Then, use as follows...
keyboard.methodName(params);

Input Management
Method	Description
clearInput	Clear the keyboard's input.
getInput	Get the keyboard's input (You can also get it from the onChange prop).
setInput	Set the keyboard's input.
replaceInput	Replace the input object completely.
Caret Position Management
Method	Description
setCaretPosition	Changes the internal caret position.
getCaretPosition	Gets the current caret position.
Button and Theme Management
Method	Description
getButtonElement	Gets a button element (DOM element) of a given button.
addButtonTheme	Adds/Updates the buttonTheme option with a new class for given buttons.
removeButtonTheme	Removes a className from the buttonTheme option.
recurseButtons	Execute an operation on each button.
Configuration and Control
Method	Description
setOptions	Set new option or modify existing ones after initialization.
dispatch	Send a command to all simple-keyboard instances at once (if you have multiple instances).
destroy	Destroy keyboard listeners and DOM elements.