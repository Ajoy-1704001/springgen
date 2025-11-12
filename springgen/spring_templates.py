from springgen.spring_helper import get_persistence_pkg



# -------------------- IMPORTS (Context-aware) --------------------

def gen_imports(base_pkg: str, entity: str, layer: str, layer_pkgs: dict, config: dict) -> str:
    """Generate minimal, context-aware imports per layer."""
    persistence_pkg = get_persistence_pkg(config)
    pagination_and_sorting = config["features"]["pagination_and_sorting"]
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
        add_if_external(layer_pkgs['entity'], entity)
        if pagination_and_sorting:
            lines += [
                "import org.springframework.data.domain.Page;",
                "import org.springframework.data.domain.Pageable;"
            ]
        else:
            lines += ["import java.util.List;"]

    elif layer == "service_impl":
        lines += [
            "import org.springframework.stereotype.Service;",
            "import lombok.RequiredArgsConstructor;"
        ]
        add_if_external(layer_pkgs['entity'], entity)
        add_if_external(layer_pkgs['repository'], f"{entity}Repository")
        add_if_external(layer_pkgs['service'], f"{entity}Service")
        
        if pagination_and_sorting:
            lines += [
                "import org.springframework.data.domain.Page;",
                "import org.springframework.data.domain.Pageable;"
            ]
        else:
            lines += ["import java.util.List;"]

    elif layer == "controller":
        lines += [
            "import org.springframework.web.bind.annotation.*;",
            "import org.springframework.http.ResponseEntity;",
            "import lombok.RequiredArgsConstructor;"
        ]
        add_if_external(layer_pkgs['entity'], entity)
        add_if_external(layer_pkgs['service'], f"{entity}Service")
        if pagination_and_sorting:
            lines += [
                "import org.springframework.data.domain.*;",
                "import org.springframework.data.web.PageableDefault;"
            ]

    return "\n".join(lines) + "\n"


# -------------------- CODE GENERATORS --------------------
def gen_entity(base_pkg, entity, layer_pkgs, config):
    return f"""{gen_imports(base_pkg, entity, "entity", layer_pkgs, config)}
@Entity
@Getter
@Setter
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
    pagination_and_sorting = config["features"]["pagination_and_sorting"]
    get_all = ""
    
    if pagination_and_sorting:
        get_all += f"""
    Page<{entity}> getPage(Pageable pageable);
        """
    else:
        get_all += f"""
    List<{entity}> getAll();
        """
    
    return f"""{gen_imports(base_pkg, entity, "service_interface", layer_pkgs, config)}
public interface {entity}Service {{

    {entity} getById(Long id);

    {entity} save({entity} obj);
    
    {entity} update({entity} obj);
    {get_all}
    void delete(Long id);
}}
"""

def gen_service_impl(base_pkg, entity, layer_pkgs, config):
    pagination_and_sorting = config["features"]["pagination_and_sorting"]
    get_all = ""
    if pagination_and_sorting:
        get_all += f"""
    @Override
    public Page<{entity}> getPage(Pageable pageable) {{
        return null;
    }}"""
    else:
        get_all += f"""
    @Override
    public List<{entity}> getAll() {{
        return null;
    }}"""
    
    return f"""{gen_imports(base_pkg, entity, "service_impl", layer_pkgs, config)}
@Service
@RequiredArgsConstructor
public class {entity}ServiceImpl implements {entity}Service {{

    private final {entity}Repository repository;
    {get_all}
    @Override
    public {entity} getById(Long id) {{
        return null;
    }}

    @Override
    public {entity} save({entity} obj) {{
        return null;
    }}
    
    @Override
    public {entity} update({entity} obj) {{
        return null;
    }}

    @Override
    public void delete(Long id) {{
        return;
    }}
}}
    """
    
def gen_service(base_pkg, entity, layer_pkgs, config):
    return gen_service_interface(base_pkg, entity, layer_pkgs, config)


def gen_controller(base_pkg, entity, layer_pkgs, config):
    lower = entity[0].lower() + entity[1:]
    pagination_and_sorting = config["features"]["pagination_and_sorting"]
    
    get_all = ""
    if pagination_and_sorting:
        api = (config or {}).get("api", {})
        psize = api.get("defaultPageSize", 20)
        dsort = str(api.get("defaultSort", "")).strip()
        field, _, dirn = dsort.partition(",")
        field = field.strip()
        dirn = (dirn or "asc").strip().upper()
        dirn = "DESC" if dirn == "DESC" else "ASC"
        anno_parts = [f"page = 0", f"size = {int(psize)}"]
        if field:
            anno_parts.append(f'sort = "{field}"')
            anno_parts.append(f"direction = Sort.Direction.{dirn}")

        pageable_anno = "@PageableDefault(" + ", ".join(anno_parts) + ")"
        get_all += f"""
    @GetMapping
    public ResponseEntity<?> getAll({pageable_anno} 
        Pageable pageable) {{
        Page<{entity}> page = service.getPage(pageable);
        return ResponseEntity.ok(page);
    }}
        """
    else:
        get_all += f"""
    @GetMapping
    public ResponseEntity<?> getAll() {{
        return ResponseEntity.ok(service.getAll());
    }}
        """
    return f"""{gen_imports(base_pkg, entity, "controller", layer_pkgs, config)}
@RestController
@RequestMapping("/{lower}s")
@RequiredArgsConstructor
public class {entity}Controller {{

    private final {entity}Service service;

    @GetMapping("/{{id}}")
    public ResponseEntity<?> getById(@PathVariable Long id) {{
        return ResponseEntity.ok(service.getById(id));
    }}

    @PostMapping
    public ResponseEntity<?> create(@RequestBody {entity} obj) {{
        return ResponseEntity.ok(service.save(obj));
    }}

    @PutMapping("/{{id}}")
    public ResponseEntity<?> update(@PathVariable Long id, @RequestBody {entity} obj) {{
        return ResponseEntity.ok(service.update(obj));
    }}
    {get_all}
    @DeleteMapping("/{{id}}")
    public ResponseEntity<?> delete(@PathVariable Long id) {{
        service.delete(id);
        return ResponseEntity.noContent().build();
    }}
}}
"""
    

GENERATORS = {
    "entity": gen_entity,
    "repository": gen_repo,
    "service": gen_service,
    "service_impl": gen_service_impl,
    "controller": gen_controller
}