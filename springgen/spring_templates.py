import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from springgen.spring_helper import get_persistence_pkg

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates", "java")

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape([]),  # no HTML escaping for code
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_tpl(name: str, **context) -> str:
    return _env.get_template(name).render(**context)

# -------------------- CODE GENERATORS (all logic moved to templates) --------------------
def gen_entity(base_pkg, entity, layer_pkgs, config):
    return render_tpl(
        "entity.java.j2",
        layer="entity",
        base_pkg=base_pkg,
        entity=entity,
        layer_pkgs=layer_pkgs,
        persistence_pkg=get_persistence_pkg(config),
        config=config,
    )

def gen_repo(base_pkg, entity, layer_pkgs, config):
    return render_tpl(
        "repository.java.j2",
        layer="repository",
        base_pkg=base_pkg,
        entity=entity,
        layer_pkgs=layer_pkgs,
        persistence_pkg=get_persistence_pkg(config),
        config=config,
    )

def gen_service_interface(base_pkg, entity, layer_pkgs, config):
    return render_tpl(
        "service.java.j2",
        layer="service_interface",
        base_pkg=base_pkg,
        entity=entity,
        layer_pkgs=layer_pkgs,
        persistence_pkg=get_persistence_pkg(config),
        config=config,
    )

def gen_service_impl(base_pkg, entity, layer_pkgs, config):
    return render_tpl(
        "service_impl.java.j2",
        layer="service_impl",
        base_pkg=base_pkg,
        entity=entity,
        layer_pkgs=layer_pkgs,
        persistence_pkg=get_persistence_pkg(config),
        config=config,
    )

def gen_service(base_pkg, entity, layer_pkgs, config):
    return gen_service_interface(base_pkg, entity, layer_pkgs, config)

def gen_controller(base_pkg, entity, layer_pkgs, config):
    lower = entity[0].lower() + entity[1:]
    return render_tpl(
        "controller.java.j2",
        layer="controller",
        base_pkg=base_pkg,
        entity=entity,
        lower=lower,
        layer_pkgs=layer_pkgs,
        persistence_pkg=get_persistence_pkg(config),
        config=config,
    )

GENERATORS = {
    "entity": gen_entity,
    "repository": gen_repo,
    "service": gen_service,
    "service_impl": gen_service_impl,
    "controller": gen_controller
}