# Template Constructor

Templates define the register map of each installation. Every template is a JSON document with:

- `devices`: list of RS-485 nodes or direct GPIO peripherals
- `registers`: typed values (holding registers, coils, sensor buckets)
- `ui`: optional hints for the Vue constructor

Create new templates inside `templates/devices/<name>.json`. On the first launch AgriTroller seeds those files into the SQLite catalog stored under `~/.agritroller/agritroller.db`. After seeding you can manage templates through the API / constructor UI instead of editing JSON manually.
