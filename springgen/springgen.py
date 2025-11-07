#!/usr/bin/env python3
import os
import sys
import json
import argparse
import xml.etree.ElementTree as ET

try:
    import pyfiglet
    from termcolor import colored
except ImportError:
    print("Please install required packages: pip install pyfiglet termcolor")
    sys.exit(1)

BASE_SRC = "src/main/java"
CONFIG_DIR = os.path.expanduser("~/.springgen")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "folders": {
        "entity": "entity",
        "repository": "repository",
        "service": "service",
        "controller": "controller"
    }
}

# ---------- CONFIG ----------
def ensure_config():
    """Ensure that ~/.springgen/config.json exists"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(colored("⚙️  Default config created at ~/.springgen/config.json", "yellow"))


def load_config():
    ensure_config()
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(data):
    ensure_config()
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------- UTILS ----------
def print_banner():
    text = pyfiglet.figlet_format("SpringGen", font="slant")
    print(colored(text, "cyan"))
    print(colored("💡 Spring Boot CRUD Generator CLI\n", "yellow"))


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


# ---------- BASE PACKAGE DETECTION ----------
def detect_base_package():
    pom_file = "pom.xml"
    if os.path.exists(pom_file):
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
            groupId = root.find('m:groupId', ns)
            if groupId is None:
                parent = root.find('m:parent', ns)
                groupId = parent.find('m:groupId', ns) if parent is not None else None
            artifactId = root.find('m:artifactId', ns)
            if groupId is not None and artifactId is not None:
                return f"{groupId.text}.{artifactId.text}"
        except:
            pass
    return None

def detect_persistence_package():
    pom_file = "pom.xml"
    if os.path.exists(pom_file):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(pom_file)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
            version_tag = root.find('m:version', ns)
            if version_tag is not None:
                version = version_tag.text
                if version and version.startswith("3."):
                    return "jakarta.persistence"
        except Exception:
            pass
    return "javax.persistence"

_PERSISTENCE_PKG = None
def get_persistence_pkg():
    global _PERSISTENCE_PKG
    if _PERSISTENCE_PKG is None:
        _PERSISTENCE_PKG = detect_persistence_package()
        print(colored(f"📦 Using JPA imports from: `{_PERSISTENCE_PKG}`", "green"))
    return _PERSISTENCE_PKG


def get_base_package():
    detected = detect_base_package()
    if detected:
        print(f"\n📦 Detected base package: {detected}")
        if ask_yes_no("Do you want to use this base package?", default="n"):
            return detected
    # fallback
    custom_pkg = input("Enter base package (e.g., com.example.demo): ").strip()
    while not custom_pkg:
        custom_pkg = input("Base package cannot be empty. Enter again: ").strip()
    pkg_path = os.path.join(BASE_SRC, custom_pkg.replace(".", "/"))
    ensure_dir(pkg_path)
    return custom_pkg


# ---------- CODE GENERATORS ----------
def gen_imports(base_pkg, entity, layer) -> str:
    """Generate context-aware imports depending on layer type."""
    persistence_pkg = get_persistence_pkg()

    # Common imports
    base_imports = [
        f"package {base_pkg};",
        "",
    ]

    # Layer-specific imports
    if layer == "entity":
        base_imports += [
            "import lombok.*;"
            f"import {persistence_pkg}.*;",
        ]
    elif layer == "repository":
        base_imports += [
            "import org.springframework.stereotype.Repository;",
            "import org.springframework.data.jpa.repository.JpaRepository;",
            f"import {LAYERS_PACKAGE['entity']}.{entity};",
        ]
    elif layer == "service":
        base_imports += [
            "import java.util.*;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.stereotype.Service;",
            f"import {LAYERS_PACKAGE['entity']}.{entity};",
            f"import {LAYERS_PACKAGE['repository']}.{entity}Repository;",
        ]
    elif layer == "controller":
        base_imports += [
            "import java.util.*;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.web.bind.annotation.*;",
            "import org.springframework.http.ResponseEntity;",
            f"import {LAYERS_PACKAGE['entity']}.{entity};",
            f"import {LAYERS_PACKAGE['service']}.{entity}Service;",
        ]

    return "\n".join(base_imports) + "\n"

def gen_entity(base_pkg, entity):
    return f"""{gen_imports(base_pkg, entity, "entity")}
@Entity
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class {entity} {{
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
}}
"""

def gen_repo(base_pkg, entity):
    return f"""{gen_imports(base_pkg, entity, "repository")}
@Repository
public interface {entity}Repository extends JpaRepository<{entity}, Long> {{}}
"""

def gen_service(base_pkg, entity):
    return f"""{gen_imports(base_pkg, entity, "service")}
@Service
public class {entity}Service {{

    @Autowired
    private {entity}Repository repository;

    public List<{entity}> getAll() {{ return new ArrayList<>(); }}

    public {entity} getById(Long id) {{ return null; }}

    public {entity} save({entity} obj) {{ return obj; }}
    
    public {entity} update({entity} obj) {{ return obj; }}

    public void delete(Long id) {{ return; }}
}}
"""

def gen_controller(base_pkg, entity):
    lower = entity[0].lower() + entity[1:]
    return f"""{gen_imports(base_pkg, entity, "controller")}
@RestController
@RequestMapping("/{lower}")
public class {entity}Controller {{

    @Autowired
    private {entity}Service service;
    
    @PostMapping
    public ResponseEntity<?> create(@RequestBody {entity} e) {{
        return ResponseEntity.ok(service.save(e));
    }}

    @GetMapping("/all")
    public ResponseEntity<?> getAll() {{
        return ResponseEntity.ok(service.getAll());
    }}

    @GetMapping("/{{id}}")
    public ResponseEntity<?> getById(@PathVariable Long id) {{
        return ResponseEntity.ok(service.getById(id));
    }}

    @PutMapping("/{{id}}")
    public ResponseEntity<?> update(@PathVariable Long id, @RequestBody {entity} e) {{
        return ResponseEntity.ok(service.update(e));
    }}

    @DeleteMapping("/{{id}}")
    public ResponseEntity<?> delete(@PathVariable Long id) {{
        service.delete(id);
        return ResponseEntity.ok(null);
    }}
}}
"""

GENERATORS = {
    "entity": gen_entity,
    "repository": gen_repo,
    "service": gen_service,
    "controller": gen_controller
}

LAYERS_PACKAGE = {}


# ---------- MAIN ----------
def main():
    print_banner()
    config = load_config()

    parser = argparse.ArgumentParser(description="Spring Boot CRUD generator")
    parser.add_argument("entities", nargs="*", help="Entity names (optional)")
    parser.add_argument("--single-folder", type=str, help="Generate all files in a single package/folder")
    parser.add_argument("--config", action="store_true", help="Edit folder naming config")
    args = parser.parse_args()

    if args.config:
        print(json.dumps(config, indent=4))
        if ask_yes_no("Do you want to modify folder names?", "n"):
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

    # Folder structure
    if args.single_folder:
        base_pkg_used = args.single_folder
        base_path = os.path.join(BASE_SRC, base_pkg_used.replace(".", "/"))
        print(f"📂 Using single folder/package: {args.single_folder}")
    else:
        base_pkg_used = get_base_package()
        base_path = os.path.join(BASE_SRC, base_pkg_used.replace(".", "/"))

    # Layers
    print("\nEntity layer is mandatory and will be generated for all entities.")
    layers_to_generate = ["entity"]
    for layer in ["repository", "service", "controller"]:
        if ask_yes_no(f"Do you want to generate {layer.capitalize()} layer for all entities?"):
            layers_to_generate.append(layer)

    # Generate files
    for entity in entities:
        print(f"\n🔹 Generating for entity: {entity}")
        for layer in layers_to_generate:
            folder_name = config["folders"][layer]
            if args.single_folder:
                path = os.path.join(base_path, f"{entity}{layer.capitalize()}.java" if layer != "entity" else f"{entity}.java")
                content = GENERATORS[layer](base_pkg_used, entity)
            else:
                layer_pkg = f"{base_pkg_used}.{folder_name}"
                LAYERS_PACKAGE[layer]=layer_pkg
                path = os.path.join(base_path, f"{folder_name}/{entity if layer=='entity' else entity+layer.capitalize()}.java")
                content = GENERATORS[layer](layer_pkg, entity)
            write_file(path, content)

    print("\n🎉 CRUD boilerplate generation complete!")


if __name__ == "__main__":
    main()
