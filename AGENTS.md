# Repository Guidelines

## Platform Overview
AgriTroller manages greenhouse/hydroponics hardware composed of a display, an SBC, and an ESP32-S2 connected via USB (HID keyboard passthrough) plus UART for GPIO/backlight commands. The software stack is a monorepo with three primary blocks:

1. **Python orchestrator** (`agritroller/`) with a web server and service layer.
2. **ESP32-S2 firmware** (`firmware/`) for HID + UART workflows.
3. **Vue frontend** (`frontend/`) for the UI constructor and dashboards.

Templates stored under `templates/` describe device register maps (JSON) and feed both backend services and the constructor UI.

## Project Structure & Module Organization
- Python entry point: `main.py` bootstraps `agritroller/`.
- Core package layout:
  - `agritroller/app.py` — service container and wiring.
  - `agritroller/services/` — modular services (DB, frontend bridge, RS-485, ESP UART, scheduler, logic, firmware updates, template manager, version registry, web server wrapper). Keep adapters (e.g., `rs485.py`, `esp_uart.py`) separate from orchestration (`logic.py`, `scheduler.py`) for easier mocking.
  - `agritroller/db/` — lightweight migration registry; migrations run automatically on boot.
  - `agritroller/web/` — FastAPI server powering `/api` and static Vue assets.
- `firmware/` hosts PlatformIO/ESP-IDF projects and resulting binaries for OTA staging.
- `frontend/` contains the Vue (Quasar) workspace; UI defaults to a dark console theme and compiles into `frontend/dist/`.
- `templates/` holds constructor JSON seeds; place user-generated maps under `templates/devices/` and keep README notes updated for template schema changes—the first backend launch imports these JSON files into SQLite so future edits happen through the app.
- Persistent runtime state lives in `~/.agritroller/` (SQLite database + `versions.json`). Never commit files from that directory.

When adding features, mirror Python modules with `tests/` counterparts (`tests/services/test_scheduler.py`, etc.) and document any new template keys.

## Build, Test, and Development Commands
- `python -m venv .venv` — create the local interpreter.
- `source .venv/bin/activate` or `.venv\Scripts\activate` — enter the venv.
- `pip install -r requirements.txt` — sync backend dependencies.
- `python main.py` or `scripts/run_backend.sh` — run the orchestrator (applies SQLite migrations in `~/.agritroller/agritroller.db`, seeds templates, ensures `versions.json`, then starts FastAPI/uvicorn). Export `AGRITROLLER_LOG_LEVEL=DEBUG` for verbose logs.
- REST endpoints live under `http://localhost:8080/api` (health, versions, system metrics, templates). Static Vue assets (from `frontend/dist/`) are exposed under `/app`.
- `pytest -q` — backend tests; combine with `-k` or `--maxfail=1` as needed.
- `npm install && npm run dev` (inside `frontend/`) — run the Vue constructor (dark theme). Set `VITE_API_BASE_URL` (default `http://localhost:8080/api`) to point at the Python server.
- Frontend dev server normally listens on port **9000** (Quasar); use `npm run dev -- --host --port 9000` if overriding.
- `npm run build` (inside `frontend/`) — emit static assets consumed by the Python web service.
- Firmware builds depend on ESP-IDF/PlatformIO targets; document the exact command near the firmware sources and drop compiled binaries into `firmware/`.

## Coding Style & Naming Conventions
Use PEP 8 defaults for Python. Provide type hints on new functions/classes, keep constants in ALL_CAPS near module tops, and avoid wildcard imports. Break large service classes into helpers when they start keeping state. For Vue, follow the official style guide (script setup, SCSS modules), keep the dark palette consistent (Quasar brand colors defined in `quasar.config.ts`), and enforce ESLint/Prettier defaults. Firmware code should follow ESP-IDF formatting tools.

## Testing Guidelines
- Use pytest for backend code and keep fixtures under `tests/fixtures/`.
- Each service gets at least one happy-path and one failure-path test (RS-485 parsing, UART reconnection, scheduler calculations, template validation).
- Snapshot/CLI assertions when outputs are part of the contract (e.g., template exports, REST responses).
- Mock hardware layers (serial, GPIO, RS-485) in tests; never require real hardware for CI.
- Frontend tests live next to Vue components (Vitest), while firmware uses Unity/CMock or the ESP-IDF test runner for critical routines.

## Commit & Pull Request Guidelines
History is empty—set the example early. Use imperative subjects ≤72 chars (`Add scheduler service skeleton`). Bodies should explain motivation and noteworthy decisions (templates updated, HID map changes). Separate unrelated work into distinct commits. PRs must:
- Summarize feature scope and affected services (web, RS-485, firmware, etc.).
- Paste `pytest -q` and relevant `npm run test` output.
- Mention firmware/constructor steps required for reviewers to reproduce.

## Security & Configuration Tips
- Load secrets (device IDs, OTA URLs, credentials) from environment variables or an untracked `.env`.
- Never commit HID mappings containing sensitive customer data.
- Scrub logs that may contain telemetry before sharing.
- Confirm GPIO/serial pinouts with vendor manuals prior to field deployment.
- Keep OTA binaries signed and verify checksums before flashing.
- Treat `~/.agritroller/` as private runtime state (SQLite DB + `versions.json`); redact it from bug reports and never write secrets back into version control.
