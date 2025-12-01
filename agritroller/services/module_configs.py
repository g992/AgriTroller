"""Load and parse module configuration files."""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from jinja2 import Environment, StrictUndefined, TemplateError

from agritroller.config import ModuleConfigSettings
from agritroller.services.base import BootstrapContext, Service


REGISTER_TYPE_ALIASES = {
    "di": "discrete_input",
    "discrete_input": "discrete_input",
    "do": "coil",
    "coil": "coil",
    "ai": "input_register",
    "input": "input_register",
    "input_register": "input_register",
    "ao": "holding_register",
    "holding": "holding_register",
    "holding_register": "holding_register",
}


@dataclass
class ModuleTypeDef:
    slug: str
    name: str
    registers: List[Dict[str, Any]]
    meta: Dict[str, Any]

    def to_record(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "kind": "module_type",
            "content": {
                "slug": self.slug,
                "name": self.name,
                "registers": self.registers,
                "meta": self.meta,
            },
        }


@dataclass
class ModuleDef:
    slug: str
    name: str
    module_type: Optional[str]
    registers: List[Dict[str, Any]]
    type_registers: List[Dict[str, Any]]
    actuators: List[Dict[str, Any]]
    sensors: List[Dict[str, Any]]
    meta: Dict[str, Any]

    def to_record(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "kind": "module",
            "module_type": self.module_type,
            "content": {
                "slug": self.slug,
                "name": self.name,
                "module_type": self.module_type,
                "registers": self.registers,
                "type_registers": self.type_registers,
                "actuators": self.actuators,
                "sensors": self.sensors,
                "meta": self.meta,
            },
        }


@dataclass
class ParsedModuleConfigs:
    modules: List[ModuleDef]
    module_types: List[ModuleTypeDef]


class ModuleConfigParser:
    """Parse Jinja2 rendered .cfg files into module definitions."""

    def __init__(self) -> None:
        self.env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)

    def parse_directory(self, config_dir: Path) -> ParsedModuleConfigs:
        modules: Dict[str, ModuleDef] = {}
        module_types: Dict[str, ModuleTypeDef] = {}
        for cfg_path in sorted(config_dir.glob("*.cfg")):
            if not cfg_path.is_file():
                continue
            rendered = self._render(cfg_path)
            parsed_modules, parsed_types = self._parse_rendered(rendered, source=cfg_path)
            for mtype in parsed_types:
                if mtype.slug in module_types:
                    raise ValueError(f"Module type '{mtype.slug}' defined multiple times")
                module_types[mtype.slug] = mtype
            for module in parsed_modules:
                if module.slug in modules:
                    raise ValueError(f"Module '{module.slug}' defined multiple times")
                modules[module.slug] = module

        merged_modules = [self._merge_module_types(module, module_types) for module in modules.values()]
        return ParsedModuleConfigs(modules=merged_modules, module_types=list(module_types.values()))

    def _render(self, path: Path) -> str:
        try:
            template = self.env.from_string(path.read_text(encoding="utf-8"))
            return template.render()
        except (OSError, TemplateError) as exc:
            raise ValueError(f"Failed to render config {path}: {exc}") from exc

    def _parse_rendered(
        self, text: str, *, source: Path
    ) -> Tuple[List[ModuleDef], List[ModuleTypeDef]]:
        sections = self._split_sections(text)
        modules: Dict[str, Dict[str, Any]] = {}
        module_types: Dict[str, Dict[str, Any]] = {}
        actuators: List[Dict[str, Any]] = []
        sensors: List[Dict[str, Any]] = []

        for section_name, section_kind, kv in sections:
            if section_kind == "module":
                modules[section_name] = {
                    "meta": kv,
                    "registers": self._consume_registers(kv, source),
                }
            elif section_kind == "module_type":
                module_types[section_name] = {
                    "meta": kv,
                    "registers": self._consume_registers(kv, source),
                }
            elif section_kind == "actuator":
                actuators.append(self._build_feature(section_name, kv, source, kind="actuator"))
            elif section_kind == "sensor":
                sensors.append(self._build_feature(section_name, kv, source, kind="sensor"))
            else:
                raise ValueError(f"Unsupported section type '{section_kind}' in {source}")

        built_modules: List[ModuleDef] = []
        for slug, payload in modules.items():
            meta = payload["meta"]
            module_type = meta.pop("type", None)
            built_modules.append(
                ModuleDef(
                    slug=slug,
                    name=str(meta.get("name", slug)),
                    module_type=str(module_type) if module_type is not None else None,
                    registers=payload["registers"],
                    type_registers=[],
                    actuators=[],
                    sensors=[],
                    meta={**meta, "source": str(source)},
                )
            )

        for act in actuators:
            target = self._find_module(built_modules, act["module"], source)
            target.actuators.append(act)

        for sensor in sensors:
            target = self._find_module(built_modules, sensor["module"], source)
            target.sensors.append(sensor)

        built_types = [
            ModuleTypeDef(
                slug=slug,
                name=str(payload["meta"].get("name", slug)),
                registers=payload["registers"],
                meta={**payload["meta"], "source": str(source)},
            )
            for slug, payload in module_types.items()
        ]

        return built_modules, built_types

    def _split_sections(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        sections: List[Tuple[str, str, Dict[str, Any]]] = []
        current: Optional[Tuple[str, str, Dict[str, Any]]] = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                if current:
                    sections.append(current)
                header = line[1:-1].strip()
                parts = header.split(maxsplit=1)
                if len(parts) != 2:
                    raise ValueError(f"Section header '{line}' is invalid")
                section_kind, section_name = parts[0].strip(), parts[1].strip()
                current = (section_name, section_kind.lower(), {})
                continue
            if current is None:
                raise ValueError("Key-value pair defined before any section header")
            key, value = self._parse_kv(line)
            current[2][key] = value
        if current:
            sections.append(current)
        return sections

    def _parse_kv(self, line: str) -> Tuple[str, str]:
        if "=" not in line:
            raise ValueError(f"Line '{line}' is not a key=value pair")
        key, value = line.split("=", 1)
        return key.strip(), value.strip()

    def _consume_registers(self, kv: Dict[str, Any], source: Path) -> List[Dict[str, Any]]:
        register_items: Dict[str, Dict[str, Any]] = {}
        for key in list(kv.keys()):
            if not key.startswith("register."):
                continue
            _, rest = key.split("register.", 1)
            if "." not in rest:
                raise ValueError(f"Register key '{key}' in {source} must be register.<name>.<field>")
            reg_name, field = rest.split(".", 1)
            register_items.setdefault(reg_name, {})[field] = kv.pop(key)

        registers: List[Dict[str, Any]] = []
        for reg_name, fields in register_items.items():
            registers.append(self._parse_register_fields(reg_name, fields, source))
        return registers

    def _parse_register_fields(self, name: str, fields: Dict[str, Any], source: Path) -> Dict[str, Any]:
        reg_type_raw = fields.get("type")
        addr_raw = fields.get("addr") or fields.get("address")
        length_raw = fields.get("length")
        required = (("type", reg_type_raw), ("addr", addr_raw), ("length", length_raw))
        missing = [label for label, raw in required if raw is None]
        if missing:
            raise ValueError(f"Register '{name}' in {source} is missing required field(s): {', '.join(missing)}")
        reg_type = self._normalize_register_type(str(reg_type_raw), source)
        address = self._parse_int(str(addr_raw))
        length = int(self._parse_scalar(str(length_raw)))

        register: Dict[str, Any] = {
            "name": name,
            "register_type": reg_type,
            "address": address,
            "length": length,
        }
        for key, raw_value in fields.items():
            if key in {"type", "addr", "address", "length"}:
                continue
            register[key] = self._parse_scalar(str(raw_value))
        return register


    def _normalize_register_type(self, raw: str, source: Path) -> str:
        lowered = raw.lower()
        if lowered not in REGISTER_TYPE_ALIASES:
            raise ValueError(f"Unknown register type '{raw}' in {source}")
        return REGISTER_TYPE_ALIASES[lowered]

    def _parse_int(self, raw: str) -> int:
        base = 16 if raw.lower().startswith("0x") else 10
        return int(raw, base=base)

    def _parse_scalar(self, raw: str) -> Any:
        lowered = raw.lower()
        if lowered in ("true", "yes", "on"):
            return True
        if lowered in ("false", "no", "off"):
            return False
        try:
            if raw.startswith("0x") or raw.startswith("0X"):
                return int(raw, 16)
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    def _build_feature(self, slug: str, kv: Dict[str, Any], source: Path, *, kind: str) -> Dict[str, Any]:
        registers = self._consume_registers(kv, source)
        if not registers:
            raise ValueError(f"{kind.title()} '{slug}' in {source} must declare at least one register")
        module_slug = str(kv.pop("module", slug))
        meta = {**kv, "source": str(source)}
        return {
            "slug": slug,
            "module": module_slug,
            "registers": registers,
            "meta": meta,
        }

    def _find_module(self, modules: Iterable[ModuleDef], slug: str, source: Path) -> ModuleDef:
        for module in modules:
            if module.slug == slug:
                return module
        raise ValueError(f"Referenced module '{slug}' not found in {source}")

    def _merge_module_types(self, module: ModuleDef, module_types: Dict[str, ModuleTypeDef]) -> ModuleDef:
        if not module.module_type:
            return module
        if module.module_type not in module_types:
            raise ValueError(f"Module '{module.slug}' references missing type '{module.module_type}'")
        base = module_types[module.module_type]
        module.type_registers = base.registers
        return module


class ModuleConfigService(Service):
    """Loads .cfg module descriptions into SQLite."""

    def __init__(self, context: BootstrapContext, config: ModuleConfigSettings) -> None:
        super().__init__("module_configs", context)
        self.config = config
        self.parser = ModuleConfigParser()
        self._modules: List[ModuleDef] = []
        self._module_types: List[ModuleTypeDef] = []

    async def _start(self) -> None:
        user_dir = Path(self.config.user_configs_dir)
        repo_dir = Path(self.config.repo_configs_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._seed_user_configs, repo_dir, user_dir)
        await asyncio.to_thread(self._load_and_persist, user_dir)
        self.context.state["module_config_service"] = self
        self.context.state["module_configs"] = [m.to_record() for m in self._modules]
        self.logger.info(
            "Loaded %d module configs and %d module types from %s",
            len(self._modules),
            len(self._module_types),
            user_dir,
        )

    async def _stop(self) -> None:
        self.context.state.pop("module_config_service", None)
        self.context.state.pop("module_configs", None)
        self._modules = []
        self._module_types = []

    def list_modules(self) -> List[Dict[str, Any]]:
        return [module.to_record() for module in self._modules]

    def list_module_types(self) -> List[Dict[str, Any]]:
        return [module_type.to_record() for module_type in self._module_types]

    def reload(self) -> None:
        self._load_and_persist(Path(self.config.user_configs_dir))

    def save_module_type(self, payload: Dict[str, Any], *, overwrite: bool = False) -> ModuleTypeDef:
        slug = payload.get("slug")
        if not slug:
            raise ValueError("Module type slug is required")
        target = self._existing_path(slug, kind="module_type") or self._resolve_target_path(
            slug, kind="module_type", meta=payload.get("meta")
        )
        if target.exists() and not overwrite:
            raise ValueError(f"Module type '{slug}' уже существует")

        text = self._render_module_type(slug, payload)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._delete_other_definitions(slug, kind="module_type", keep=target)
        target.write_text(text, encoding="utf-8")
        self.reload()
        updated = next((m for m in self._module_types if m.slug == slug), None)
        if not updated:
            raise RuntimeError("Module type was not persisted")
        return updated

    def save_module(self, payload: Dict[str, Any], *, overwrite: bool = False) -> ModuleDef:
        slug = payload.get("slug")
        if not slug:
            raise ValueError("Module slug is required")
        target = self._existing_path(slug, kind="module") or self._resolve_target_path(
            slug, kind="module", meta=payload.get("meta")
        )
        if target.exists() and not overwrite:
            raise ValueError(f"Module '{slug}' уже существует")

        text = self._render_module(slug, payload)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._delete_other_definitions(slug, kind="module", keep=target)
        target.write_text(text, encoding="utf-8")
        self.reload()
        updated = next((m for m in self._modules if m.slug == slug), None)
        if not updated:
            raise RuntimeError("Module was not persisted")
        return updated

    def delete_config(self, slug: str, *, kind: str) -> bool:
        user_dir = Path(self.config.user_configs_dir)
        target = self._resolve_target_path(slug, kind=kind)
        if not target.exists():
            return False
        target.unlink()
        self.reload()
        return True

    def _load_and_persist(self, user_dir: Path) -> None:
        conn = self._get_conn()
        try:
            parsed = self.parser.parse_directory(user_dir)
        except ValueError as exc:
            self.logger.error("Failed to parse module configs: %s", exc)
            raise
        self._modules = parsed.modules
        self._module_types = parsed.module_types
        self._persist(conn, parsed)
        self.context.state["module_configs"] = [m.to_record() for m in self._modules]
        self.context.state["module_config_types"] = [t.to_record() for t in self._module_types]

    def _seed_user_configs(self, repo_dir: Path, user_dir: Path) -> None:
        if not repo_dir.exists():
            self.logger.warning("Repo config directory %s does not exist", repo_dir)
            return
        for cfg_path in sorted(repo_dir.glob("*.cfg")):
            destination = user_dir / cfg_path.name
            if destination.exists():
                continue
            try:
                shutil.copy(cfg_path, destination)
                self.logger.info("Seeded config %s -> %s", cfg_path, destination)
            except OSError as exc:
                self.logger.error("Failed to seed %s: %s", cfg_path, exc)

    def _persist(self, conn: Any, parsed: ParsedModuleConfigs) -> None:
        conn.execute("DELETE FROM module_configs")
        for record in parsed.module_types + parsed.modules:
            payload = record.to_record()
            conn.execute(
                """
                INSERT INTO module_configs (slug, kind, name, module_type, content)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slug, kind) DO UPDATE SET
                    name=excluded.name,
                    module_type=excluded.module_type,
                    content=excluded.content,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    payload.get("slug"),
                    payload.get("kind"),
                    payload.get("name"),
                    payload.get("module_type"),
                    json.dumps(payload.get("content"), ensure_ascii=False),
                ),
            )
        conn.commit()

    def _resolve_target_path(self, slug: str, *, kind: str, meta: Optional[Dict[str, Any]] = None) -> Path:
        user_dir = Path(self.config.user_configs_dir)
        source = None
        if meta and isinstance(meta, dict):
            source = meta.get("source")
        if source:
            source_path = Path(str(source))
            try:
                source_path.relative_to(user_dir)
                return source_path
            except ValueError:
                pass
        prefix = "module_type" if kind == "module_type" else "module"
        return user_dir / f"{prefix}_{slug}.cfg"

    def _existing_path(self, slug: str, *, kind: str) -> Optional[Path]:
        records = self._module_types if kind == "module_type" else self._modules
        for record in records:
            if record.slug != slug:
                continue
            meta = record.meta or {}
            source = meta.get("source") if isinstance(meta, dict) else None
            if source:
                return Path(str(source))
        return None

    def _delete_other_definitions(self, slug: str, *, kind: str, keep: Path) -> None:
        user_dir = Path(self.config.user_configs_dir)
        for cfg_path in user_dir.glob("*.cfg"):
            if cfg_path.resolve() == keep.resolve():
                continue
            try:
                text = cfg_path.read_text(encoding="utf-8")
            except OSError:
                continue
            header = f"[{kind} {slug}]"
            if header in text:
                cfg_path.unlink(missing_ok=True)

    def _render_header(self, kind: str, slug: str, payload: Dict[str, Any]) -> List[str]:
        lines = [f"[{kind} {slug}]"]
        if payload.get("name"):
            lines.append(f"name = {payload['name']}")
        if payload.get("description"):
            lines.append(f"description = {payload['description']}")
        if kind == "module" and payload.get("module_type"):
            lines.append(f"type = {payload['module_type']}")
        return lines

    def _render_register_lines(self, register: Dict[str, Any]) -> List[str]:
        required = {"name", "register_type", "address", "length"}
        missing = [field for field in required if field not in register]
        if missing:
            raise ValueError(f"Register '{register}' missing required fields: {', '.join(missing)}")

        reg_type = REGISTER_TYPE_ALIASES.get(str(register["register_type"]).lower())
        if not reg_type:
            raise ValueError(f"Unknown register type '{register.get('register_type')}'")
        address = self._format_int(register["address"])
        length = self._scalar_to_str(register.get("length", 1))

        prefix = f"register.{register['name']}"
        lines = [f"{prefix}.type = {reg_type}"]
        lines.append(f"{prefix}.addr = {address}")
        lines.append(f"{prefix}.length = {length}")
        for key, value in register.items():
            if key in required:
                continue
            lines.append(f"{prefix}.{key} = {self._scalar_to_str(value)}")
        return lines

    def _render_feature(self, feature: Dict[str, Any], *, kind: str, module_slug: str) -> List[str]:
        slug = feature.get("slug") or feature.get("name")
        if not slug:
            raise ValueError(f"{kind.title()} section missing slug")
        lines = ["", f"[{kind} {slug}]"]
        lines.append(f"module = {module_slug}")
        registers = feature.get("registers") or []
        if not registers:
            raise ValueError(f"{kind.title()} '{slug}' must include at least one register")
        for register in registers:
            lines.extend(self._render_register_lines(register))
        return lines

    def _render_module_type(self, slug: str, payload: Dict[str, Any]) -> str:
        lines = self._render_header("module_type", slug, payload)
        registers = payload.get("registers") or []
        for register in registers:
            lines.extend(self._render_register_lines(register))
        return "\n".join(lines) + "\n"

    def _render_module(self, slug: str, payload: Dict[str, Any]) -> str:
        lines = self._render_header("module", slug, payload)
        registers = payload.get("registers") or []
        for register in registers:
            lines.extend(self._render_register_lines(register))

        for feature in payload.get("actuators") or []:
            lines.extend(self._render_feature(feature, kind="actuator", module_slug=slug))

        for feature in payload.get("sensors") or []:
            lines.extend(self._render_feature(feature, kind="sensor", module_slug=slug))

        return "\n".join(lines) + "\n"

    def _scalar_to_str(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    def _format_int(self, value: Any) -> str:
        try:
            intval = int(value)
        except (TypeError, ValueError):
            return str(value)
        return hex(intval) if intval >= 16 else str(intval)

    def _get_conn(self) -> Any:
        conn = self.context.state.get("db_conn")
        if conn is None:
            raise RuntimeError("Database connection not ready for ModuleConfigService")
        return conn
