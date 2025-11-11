#!/usr/bin/env python3
import os
import sys
import json
import argparse
import xml.etree.ElementTree as ET

from springgen.spring_templates import GENERATORS
from springgen.utils import print_banner

try:
    from termcolor import colored
except ImportError:
    print("Please install required packages: pip install pyfiglet termcolor")
    sys.exit(1)

# -------------------- CONSTANTS / CONFIG --------------------
BASE_SRC = "src/main/java"
CONFIG_DIR = os.path.expanduser("~/.springgen")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "base_package": "com.example.demo",
    "persistence_package": "auto",
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
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(colored("⚙️  Default config created at ~/.springgen/config.json", "yellow"))

def load_config():
    ensure_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    ensure_config()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

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


# -------------------- MAIN --------------------
def main():
    print_banner()
    config = load_config()

    parser = argparse.ArgumentParser(description="Spring Boot CRUD generator")
    parser.add_argument("entities", nargs="*", help="Entity names (optional)")
    parser.add_argument("--single-folder", type=str, help="Put all files inside a single folder under the base package")
    parser.add_argument("--config", action="store_true", help="Edit settings (base_package, folders, persistence_package)")
    args = parser.parse_args()

    if args.config:
        print(json.dumps(config, indent=4))
        if ask_yes_no("Do you want to modify settings?", "n"):
            # base package
            new_bp = input(f"base_package [{config.get('base_package','')}]: ").strip()
            if new_bp:
                config["base_package"] = new_bp
            # persistence package
            pp = config.get("persistence_package", "auto")
            new_pp = input(f"persistence_package (jakarta.persistence / javax.persistence / auto) [{pp}]: ").strip()
            if new_pp:
                config["persistence_package"] = new_pp
            # folder names
            for k, v in config["folders"].items():
                new_v = input(f"{k} folder name [{v}]: ").strip()
                if new_v:
                    config["folders"][k] = new_v
            save_config(config)
            print(colored("✅ Config updated successfully!", "green"))
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
    if ask_yes_no(f"Do you want to generate Repository layer for all entities?"):
        layers_to_generate.append("repository")

    # Service? (interface + impl together)
    if ask_yes_no(f"Do you want to generate Service layer (interface + impl) for all entities?"):
        layers_to_generate.append("service")
        layers_to_generate.append("service_impl")

    # Controller?
    if ask_yes_no(f"Do you want to generate Controller layer for all entities?"):
        layers_to_generate.append("controller")

    # Generate files
    for entity in entities:
        print(f"\n🔹 Generating for entity: {entity}")
        for layer in layers_to_generate:
            pkg = layer_pkgs[layer]
            base_path = os.path.join(BASE_SRC, pkg.replace(".", "/"))
            filename = f"{entity}.java" if layer == "entity" else (f"{entity}ServiceImpl.java" 
                                                                   if layer=="service_impl" 
                                                                   else f"{entity}{layer.capitalize()}.java")
            content = GENERATORS[layer](pkg, entity, layer_pkgs, config)
            path = os.path.join(base_path, filename)
            write_file(path, content)

    print("\n🎉 CRUD boilerplate generation complete!")

if __name__ == "__main__":
    main()
