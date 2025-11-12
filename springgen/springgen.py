#!/usr/bin/env python3
import os
import sys
import json
import argparse
import xml.etree.ElementTree as ET
import shlex
import subprocess

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

def load_config():
    """Load YAML config if present; else fallback to legacy JSON; else default."""
    ensure_config()
    if os.path.exists(CONFIG_FILE) and yaml is not None:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    legacy_json = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(legacy_json):
        with open(legacy_json, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(DEFAULT_CONFIG)

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
