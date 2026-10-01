"""docs-server containerized component."""
from jejune_cli.component_containerized import cont_comp


class comp_docs_server(cont_comp):
    def __init__(self) -> None:
        super().__init__(
            name="docs-server",
            image_name="jejune-docs-server",
            service_name="docs-server",
            hint="run `jejune build`",
        )
        self.repos = [("DockerContext", "DOCS_SERVER_CONTEXT")]
        if self._context.ecosystem is not None:
            self.conditional_dependencies = [(lambda: not self.is_available(), self._context.ecosystem)]

    def is_available(self) -> bool:
        return self.is_built()

    def is_running(self) -> tuple[bool, str]:
        from pathlib import Path
        deploy_name = Path(".").resolve().name.lower()
        return super().is_running(f"jejune-{deploy_name}-{self.service_name}-1")
