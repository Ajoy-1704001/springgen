#!/usr/bin/env python3
import os
import sys
import json
import argparse
import xml.etree.ElementTree as ET
import shlex
import subprocess
import copy
from springgen.spring_templates import GENERATORS
from springgen.utils import print_banner

try:
    from termcolor import colored
except ImportError:
    print("Please install required packages: pip install pyfiglet termcolor")
    sys.exit(1)

# Optional YAML support
try:
    import yaml
except Exception:
    yaml = None

# -------------------- CONSTANTS / CONFIG --------------------
BASE_SRC = "src/main/java"
CONFIG_DIR = os.path.expanduser("~/.springgen")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yml")

DEFAULT_CONFIG = {
    "base_package": "com.example.demo",
    "persistence_package": "auto",  # "jakarta.persistence" | "javax.persistence" | "auto"
    "features": {
        "pagination_and_sorting": True
    },
    "api": {
        "defaultPageSize": 10,
        "defaultSort": "id,asc"
    },
    "folders": {
        "entity": "model",
        "repository": "repository",
        "service": "service",
        "controller": "controller"
    },
    "entity": {
        "primary_key": {
            "type": "Long",
            "strategy": "IDENTITY"
        }
    }
}

MAVEN_NS = {'m': 'http://maven.apache.org/POM/4.0.0'}

# -------------------- CONFIG HELPERS --------------------
def ensure_config():
    """Ensure config directory and a config file exist. Prefer YAML; fallback to JSON if PyYAML missing."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        if yaml is None:
            alt = os.path.join(CONFIG_DIR, "config.json")
            with open(alt, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            print(colored(f"⚙️  PyYAML not installed. Wrote JSON: {alt}", "yellow"))
        else:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                yaml.safe_dump(DEFAULT_CONFIG, f, sort_keys=False)
            print(colored(f"⚙️  Default YAML config created at {CONFIG_FILE}", "yellow"))
            
def deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base. Returns a new dict.
    - base: defaults
    - override: user config
    """
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if (
            key in result 
            and isinstance(result[key], dict) 
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def load_config():
    """Load config from file and merge with defaults so new keys are available."""
    ensure_config()
    user_cfg = {}

    if os.path.exists(CONFIG_FILE) and yaml is not None:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
    else:
        legacy_json = os.path.join(CONFIG_DIR, "config.json")
        if os.path.exists(legacy_json):
            with open(legacy_json, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)

    cfg = deep_merge(DEFAULT_CONFIG, user_cfg)
    return cfg


def save_config(data):
    """Save as YAML if possible; else JSON fallback."""
    ensure_config()
    if yaml is not None:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    else:
        alt = os.path.join(CONFIG_DIR, "config.json")
        with open(alt, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(colored(f"⚠️  Saved config as JSON (PyYAML missing): {alt}", "yellow"))

def ask_yes_no(question, default="y"):
    ans = input(f"{question} [y/n] (default {default}): ").strip().lower()
    if not ans:
        ans = default
    return ans.startswith("y")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def write_file(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Created {path}")

def _parse_value(v: str):
    """Heuristic parse for --set values: bool/int/float/str."""
    vl = str(v).strip()
    if vl.lower() in ("true", "false"):
        return vl.lower() == "true"
    try:
        if "." in vl:
            return float(vl)
        return int(vl)
    except ValueError:
        return vl

def set_keypath(cfg: dict, keypath: str, value):
    """
    Set nested key by dot.path, e.g.:
      features.pagination_and_sorting=true
      api.defaultPageSize=50
      folders.entity=model
    """
    parts = [p for p in keypath.split(".") if p]
    if not parts:
        return
    cur = cfg
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

def get_default_editor():
    ed = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if ed:
        return ed
    if os.name == "nt":
        return "notepad"
    # Sensible UNIX-ish fallbacks
    # Try VS Code wait flag first so the script pauses until file is closed.
    return "code -w" if _which("code") else ("nano" if _which("nano") else "vi")

def _which(cmd):
    from shutil import which
    return which(cmd) is not None

def open_in_editor(path: str):
    editor = get_default_editor()
    try:
        cmd = shlex.split(editor) + [path]
        subprocess.call(cmd)
    except Exception as e:
        print(colored(f"⚠️  Failed to open editor '{editor}': {e}", "yellow"))
        print(colored(f"   Please edit the file manually: {path}", "yellow"))

PK_TYPE_CHOICES = ["Long", "UUID", "String", "Integer"]
PK_STRATEGY_CHOICES = ["IDENTITY", "AUTO", "SEQUENCE", "NONE"]  # NONE = no @GeneratedValue


def ask_choice(prompt: str, options, default_index: int = 0) -> str:
    """
    Ask user to choose from a list (numeric or free-text).
    Returns chosen value (string).
    """
    while True:
        print(prompt)
        for i, opt in enumerate(options, 1):
            default_marker = " (default)" if i - 1 == default_index else ""
            print(f"  {i}) {opt}{default_marker}")
        ans = input(f"Enter choice [{default_index + 1}] or type value: ").strip()

        if not ans:
            return options[default_index]

        if ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(options):
                return options[idx]

        # treat as raw value (user typed custom type/strategy)
        return ans


def ensure_primary_key_config(config: dict) -> dict:
    """
    Ensure global entity.primary_key config exists with:
      - name
      - type
      - strategy
    If missing, ask once and persist to config file.
    """
    entity_cfg = config.setdefault("entity", {})
    pk_cfg = entity_cfg.setdefault("primary_key", {})

    modified = False

    if not pk_cfg.get("name"):
        pk_cfg["name"] = "id"
        modified = True

    if not pk_cfg.get("type"):
        print("\n🔑 Configure default primary key type for all entities")
        pk_cfg["type"] = ask_choice(
            "Choose default primary key Java type:",
            PK_TYPE_CHOICES,
            default_index=0  # Long
        )
        modified = True

    if not pk_cfg.get("strategy"):
        print("\n⚙️ Configure default primary key generation strategy")
        pk_cfg["strategy"] = ask_choice(
            "Choose default JPA GenerationType strategy:",
            PK_STRATEGY_CHOICES,
            default_index=0  # IDENTITY
        )
        modified = True

    if modified:
        save_config(config)
        print(
            colored(
                f"✅ Default PK saved: {pk_cfg['type']} {pk_cfg['name']} {pk_cfg['strategy']}",
                "green",
            )
        )

    return config


def ask_per_entity_pk_override(global_pk_cfg: dict, entity_name: str):
    """
    Ask whether to override PK config for a single entity.
    Returns:
      - None  -> use global config
      - dict  -> {"name": ..., "type": ..., "strategy": ...} for this entity ONLY (in-memory)
    """
    print(f"\n🔑 Primary key for entity: {entity_name}")
    print(
        f"Global default: {global_pk_cfg.get('type', 'Long')} "
        f"{global_pk_cfg.get('name', 'id')} "
        f"({global_pk_cfg.get('strategy', 'IDENTITY')})"
    )

    use_global = ask_yes_no("Use global primary key config for this entity?", default="y")
    if use_global:
        return None

    # Name
    default_name = global_pk_cfg.get("name", "id")
    name_input = input(
        f"Primary key field name for {entity_name} [{default_name}]: "
    ).strip()
    name = name_input or default_name

    # Type
    global_type = global_pk_cfg.get("type", "Long")
    try:
        default_type_index = PK_TYPE_CHOICES.index(global_type)
    except ValueError:
        default_type_index = 0

    pk_type = ask_choice(
        f"Choose primary key type for {entity_name}:",
        PK_TYPE_CHOICES,
        default_index=default_type_index,
    )

    # Strategy
    global_strategy = global_pk_cfg.get("strategy", "IDENTITY")
    try:
        default_strategy_index = PK_STRATEGY_CHOICES.index(global_strategy)
    except ValueError:
        default_strategy_index = 0

    strategy = ask_choice(
        f"Choose generation strategy for {entity_name}:",
        PK_STRATEGY_CHOICES,
        default_index=default_strategy_index,
    )

    return {"name": name, "type": pk_type, "strategy": strategy}


# -------------------- MAIN --------------------
def main():
    print_banner()
    config = load_config()

    parser = argparse.ArgumentParser(description="Spring Boot CRUD generator")
    parser.add_argument("entities", nargs="*", help="Entity names (optional)")
    parser.add_argument("--single-folder", type=str, help="Put all files inside a single folder under the base package")
    parser.add_argument("--config", action="store_true", help="Show current settings (then optionally edit)")
    parser.add_argument("--edit-config", action="store_true", help="Open the config file in your editor")
    parser.add_argument("--set", action="append", metavar="KEYPATH=VALUE",
                        help="Set a config value via key path (e.g., features.pagination_and_sorting=true, api.defaultPageSize=50). Can be used multiple times.")
    args = parser.parse_args()

    # Inline key updates first (allows chaining with generation)
    if args.set:
        for kv in args.set:
            if "=" not in kv:
                print(colored(f"❌ Invalid --set value: {kv} (expected KEYPATH=VALUE)", "red"))
                sys.exit(1)
            k, v = kv.split("=", 1)
            set_keypath(config, k.strip(), _parse_value(v))
        save_config(config)
        print(colored("✅ Config updated (via --set).", "green"))
        config = load_config()  # reload
        sys.exit()

    if args.config:
        # Show current config (YAML if available; else JSON)
        if yaml is not None:
            print(yaml.safe_dump(config, sort_keys=False))
        else:
            print(json.dumps(config, indent=2))
        if ask_yes_no("Open the config in your editor?", "n"):
            ensure_config()
            path = CONFIG_FILE if os.path.exists(CONFIG_FILE) else os.path.join(CONFIG_DIR, "config.json")
            open_in_editor(path)
            config = load_config()
            print(colored("✅ Config reloaded.", "green"))
        return

    if args.edit_config:
        ensure_config()
        path = CONFIG_FILE if os.path.exists(CONFIG_FILE) else os.path.join(CONFIG_DIR, "config.json")
        open_in_editor(path)
        config = load_config()
        print(colored("✅ Config reloaded.", "green"))
        return
    
    config = ensure_primary_key_config(config)
    global_pk_cfg = config.get("entity", {}).get("primary_key", {
        "name": "id",
        "type": "Long",
        "strategy": "IDENTITY",
    })

    # Entities
    if not args.entities:
        entities_input = input("Enter entity names (comma-separated): ")
        entities = [e.strip() for e in entities_input.split(",") if e.strip()]
    else:
        entities = args.entities

    if not entities:
        print("❌ You must provide at least one entity name.")
        sys.exit(1)

    # Base package is ONLY from config (no auto-detect)
    base_pkg_root = config["base_package"]

    # Single-folder support
    if args.single_folder:
        single_folder = args.single_folder.strip()
        base_pkg_used = f"{base_pkg_root}.{single_folder}"
        print(colored(f"\n📦 Using single-folder mode: {base_pkg_used}", "cyan"))
        layer_pkgs = {layer: base_pkg_used for layer in ["entity", "repository", "service", "controller"]}
        layer_pkgs["service_impl"] = base_pkg_used
    else:
        base_pkg_used = base_pkg_root
        print(colored(f"\n📦 Using base package from config: {base_pkg_used}", "cyan"))
        layer_pkgs = {
            "entity": f"{base_pkg_used}.{config['folders']['entity']}",
            "repository": f"{base_pkg_used}.{config['folders']['repository']}",
            "service": f"{base_pkg_used}.{config['folders']['service']}",
            "controller": f"{base_pkg_used}.{config['folders']['controller']}",
        }
        layer_pkgs["service_impl"] = f"{layer_pkgs['service']}.impl"

    # Ensure folder structure exists
    for pkg in set(layer_pkgs.values()):
        pkg_path = os.path.join(BASE_SRC, pkg.replace(".", "/"))
        ensure_dir(pkg_path)
        
    per_entity_pk_customization = ask_yes_no(
        "Do you want to customize primary key type/strategy per entity? (default uses global config for all)",
        default="n",
    )

    # Layers to generate
    print("\nEntity layer is mandatory and will be generated for all entities.")
    layers_to_generate = ["entity"]

    # Repository?
    if ask_yes_no("Do you want to generate Repository layer for all entities?"):
        layers_to_generate.append("repository")

    # Service? (interface + impl together)
    if ask_yes_no("Do you want to generate Service layer (interface + impl) for all entities?"):
        layers_to_generate.append("service")
        layers_to_generate.append("service_impl")

    # Controller?
    if ask_yes_no("Do you want to generate Controller layer for all entities?"):
        layers_to_generate.append("controller")

    # Generate files
    for entity in entities:
        print(f"\n🔹 Generating for entity: {entity}")
        
        if per_entity_pk_customization:
            override_pk_cfg = ask_per_entity_pk_override(global_pk_cfg, entity)
            if override_pk_cfg:
                config.setdefault("entity", {})["primary_key"] = override_pk_cfg
            else:
                config.setdefault("entity", {})["primary_key"] = global_pk_cfg
        else:
            config.setdefault("entity", {})["primary_key"] = global_pk_cfg
            
        for layer in layers_to_generate:
            pkg = layer_pkgs[layer]
            base_path = os.path.join(BASE_SRC, pkg.replace(".", "/"))
            filename = (
                f"{entity}.java" if layer == "entity"
                else (f"{entity}ServiceImpl.java" if layer == "service_impl"
                      else f"{entity}{layer.capitalize()}.java")
            )
            content = GENERATORS[layer](pkg, entity, layer_pkgs, config)
            path = os.path.join(base_path, filename)
            write_file(path, content)

    print("\n🎉 CRUD boilerplate generation complete!")

if __name__ == "__main__":
    main()
