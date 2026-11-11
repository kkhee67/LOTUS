"""Cross-file validation shared by the future importer and offline checks."""
from pathlib import Path
from shared.models import Opportunity, ResourceLink, RoleProfile, Source, OptionsResponse


def validate_dataset(*, sources: list[Source], opportunities: list[Opportunity],
                     roles: list[RoleProfile], resource_links: list[ResourceLink]) -> None:
    groups = (sources, opportunities, roles, resource_links)
    for group in groups:
        if len({x.id for x in group}) != len(group):
            raise ValueError('duplicate dataset IDs')
    kinds = {x.source_kind for group in groups for x in group}
    if len(kinds) > 1:
        raise ValueError('real and synthetic data must not be mixed')
    source_ids = {s.id for s in sources}
    catalog = OptionsResponse.model_validate_json(
        (Path(__file__).parent / 'catalog.json').read_text(encoding='utf-8'))
    field_codes = {x.code for x in catalog.fields}
    for item in (*opportunities, *roles):
        if not set(item.fields) <= field_codes:
            raise ValueError('unknown catalog field code; preserve unmapped content in text')
    for group in (opportunities, roles, resource_links):
        for item in group:
            if not set(item.source_ids) <= source_ids:
                raise ValueError('unknown source reference')
