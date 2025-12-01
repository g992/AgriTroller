Modules
Modules are able to extend and add features to simple-keyboard. Check out a list of some of the plugins available so far:

Layouts
Autocorrect
Input Mask
Key Navigation
Swipe Keyboard


How do modules work?
Modules are essentially Javascript functions (or classes) that attach to an instance of simple keyboard. They are able to create new options, edit current behavior, and more.

This gives you flexibility to adapt simple-keyboard according to your needs.

How to create my own module?
Creating your own module is easy. Just pass a function to simple-keyboard's "modules" option

const myModule = (keyboard) => {
 // Here you can modify and extend simple-keyboard
};

new Keyboard({
  onChange: input => onChange(input),
  onKeyPress: button => onKeyPress(button),
  modules: [
    myModule
  ]
});

Demos:
