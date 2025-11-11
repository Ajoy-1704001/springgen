from springgen.spring_helper import get_persistence_pkg



# -------------------- IMPORTS (Context-aware) --------------------

def gen_imports(base_pkg: str, entity: str, layer: str, layer_pkgs: dict, config: dict) -> str:
    """Generate minimal, context-aware imports per layer."""
    persistence_pkg = get_persistence_pkg(config)
    lines = [f"package {base_pkg};", ""]

    def add_if_external(target_pkg: str, type_name: str):
        if target_pkg and target_pkg != base_pkg:
            lines.append(f"import {target_pkg}.{type_name};")

    if layer == "entity":
        lines += [
            "import lombok.*;",
            f"import {persistence_pkg}.*;",
        ]

    elif layer == "repository":
        lines += [
            "import org.springframework.stereotype.Repository;",
            "import org.springframework.data.jpa.repository.JpaRepository;",
        ]
        add_if_external(layer_pkgs['entity'], entity)

    elif layer == "service_interface":
        # interface only references domain types if needed (not here)
        lines += [
            "import java.util.List;",
        ]
        add_if_external(layer_pkgs['entity'], entity)

    elif layer == "service_impl":
        lines += [
            "import java.util.List;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.stereotype.Service;",
        ]
        add_if_external(layer_pkgs['entity'], entity)
        add_if_external(layer_pkgs['repository'], f"{entity}Repository")
        add_if_external(layer_pkgs['service'], f"{entity}Service")

    elif layer == "controller":
        lines += [
            "import java.util.List;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.web.bind.annotation.*;",
        ]
        add_if_external(layer_pkgs['entity'], entity)
        add_if_external(layer_pkgs['service'], f"{entity}Service")

    return "\n".join(lines) + "\n"


# -------------------- CODE GENERATORS --------------------
def gen_entity(base_pkg, entity, layer_pkgs, config):
    return f"""{gen_imports(base_pkg, entity, "entity", layer_pkgs, config)}
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

def gen_repo(base_pkg, entity, layer_pkgs, config):
    return f"""{gen_imports(base_pkg, entity, "repository", layer_pkgs, config)}
@Repository
public interface {entity}Repository extends JpaRepository<{entity}, Long> {{}}
"""

def gen_service_interface(base_pkg, entity, layer_pkgs, config):
    return f"""{gen_imports(base_pkg, entity, "service_interface", layer_pkgs, config)}
public interface {entity}Service {{

    List<{entity}> getAll();

    {entity} getById(Long id);

    {entity} save({entity} obj);
    
    {entity} update({entity} obj);

    void delete(Long id);
}}
"""

def gen_service_impl(base_pkg, entity, layer_pkgs, config):
    return f"""{gen_imports(base_pkg, entity, "service_impl", layer_pkgs, config)}
@Service
public class {entity}ServiceImpl implements {entity}Service {{

    @Autowired
    private {entity}Repository repository;

    @Override
    public List<{entity}> getAll() {{ return null; }}

    @Override
    public {entity} getById(Long id) {{ return null; }}

    @Override
    public {entity} save({entity} obj) {{ return null; }}
    
    @Override
    public {entity} update({entity} obj) {{ return null; }}

    @Override
    public void delete(Long id) {{ return; }}
}}
    """
    
def gen_service(base_pkg, entity, layer_pkgs, config):
    return gen_service_interface(base_pkg, entity, layer_pkgs, config)


def gen_controller(base_pkg, entity, layer_pkgs, config):
    lower = entity[0].lower() + entity[1:]
    return f"""{gen_imports(base_pkg, entity, "controller", layer_pkgs, config)}
@RestController
@RequestMapping("/api/{lower}")
public class {entity}Controller {{

    @Autowired
    private {entity}Service service;

    @GetMapping("/all")
    public List<{entity}> getAll() {{ return service.getAll(); }}

    @GetMapping("/{{id}}")
    public {entity} getById(@PathVariable Long id) {{ return service.getById(id); }}

    @PostMapping
    public {entity} create(@RequestBody {entity} e) {{ return service.save(e); }}

    @PutMapping("/{{id}}")
    public {entity} update(@PathVariable Long id, @RequestBody {entity} e) {{
        return service.save(e);
    }}

    @DeleteMapping("/{{id}}")
    public void delete(@PathVariable Long id) {{ service.delete(id); }}
}}
"""
    

GENERATORS = {
    "entity": gen_entity,
    "repository": gen_repo,
    "service": gen_service,
    "service_impl": gen_service_impl,
    "controller": gen_controller
}