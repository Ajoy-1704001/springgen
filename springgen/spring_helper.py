import sys, os
import xml.etree.ElementTree as ET
try:
    from termcolor import colored
except ImportError:
    print("Please install required packages: pip install pyfiglet termcolor")
    sys.exit(1)
    

MAVEN_NS = {'m': 'http://maven.apache.org/POM/4.0.0'}    


# -------------------- (Optional) Detect persistence package --------------------
def _parse_semver(v: str):
    if not v:
        return (0, 0, 0)
    parts = v.split(".")
    nums = []
    for p in parts[:3]:
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        nums.append(int(num) if num else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)

def _get_text(el):
    return el.text.strip() if el is not None and el.text else None

def _resolve_property(val, props):
    if not val:
        return val
    if val.startswith("${") and val.endswith("}"):
        key = val[2:-1]
        return props.get(key, val)
    return val

def _collect_properties(root):
    props = {}
    props_el = root.find("m:properties", MAVEN_NS)
    if props_el is not None:
        for child in list(props_el):
            tag = child.tag.split("}")[-1]
            props[tag] = _get_text(child)
    return props

def _detect_spring_boot_version_from_parent(root, props):
    parent = root.find("m:parent", MAVEN_NS)
    if parent is None:
        return None
    g = _get_text(parent.find("m:groupId", MAVEN_NS))
    a = _get_text(parent.find("m:artifactId", MAVEN_NS))
    v = _resolve_property(_get_text(parent.find("m:version", MAVEN_NS)), props)
    if g == "org.springframework.boot" and a == "spring-boot-starter-parent":
        return v
    return None

def _detect_spring_boot_version_from_props(props):
    for key in ("spring-boot.version", "springboot.version", "spring_boot_version"):
        if key in props and props[key]:
            return props[key]
    return None

def detect_persistence_package_from_pom():
    """Return 'jakarta.persistence' for Boot >=3, else 'javax.persistence' (best effort)."""
    pom_file = "pom.xml"
    try:
        if os.path.exists(pom_file):
            tree = ET.parse(pom_file)
            root = tree.getroot()
            props = _collect_properties(root)
            ver = _detect_spring_boot_version_from_parent(root, props) or _detect_spring_boot_version_from_props(props)
            if ver:
                major, minor, patch = _parse_semver(_resolve_property(ver, props))
                return "jakarta.persistence" if (major, minor, patch) >= (3, 0, 0) else "javax.persistence"
    except Exception as e:
        print(colored(f"⚠️  Could not detect Spring Boot version automatically ({e}). Defaulting to javax.persistence.", "yellow"))
    return "javax.persistence"

_PERSISTENCE_PKG = None
def get_persistence_pkg(config):
    global _PERSISTENCE_PKG
    if _PERSISTENCE_PKG is None:
        forced = config.get("persistence_package", "auto")
        if forced == "auto":
            _PERSISTENCE_PKG = detect_persistence_package_from_pom()
        elif forced in ("jakarta.persistence", "javax.persistence"):
            _PERSISTENCE_PKG = forced
        else:
            print(colored(f"⚠️  Unknown persistence_package '{forced}', defaulting to javax.persistence", "yellow"))
            _PERSISTENCE_PKG = "javax.persistence"
        print(colored(f"📦 Using JPA imports from: `{_PERSISTENCE_PKG}`", "green"))
    return _PERSISTENCE_PKG