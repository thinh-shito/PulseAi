from app.domain.models.pa_templates import PATemplate
from app.infra.repositories.base_repository import BaseRepository


class TemplateRepository(BaseRepository[PATemplate]):
    """
    Template Repository extending BaseRepository for PATemplate entity.
    """
    def __init__(self):
        super().__init__(PATemplate)


template_repo = TemplateRepository()
