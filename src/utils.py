from typing import Optional, Union
from typing import Type, Literal

from fastapi import UploadFile
from pydantic import BaseModel


def create_field_map_for_model(model: Type[BaseModel]) -> dict[str, str]:
    """
    Create a bidirectional field map for the given Pydantic model.

    The map will contain:
    - snake_case field_name => snake_case field_name
    - camelCase alias => snake_case field_name

    This lets us convert either the snake_case or the camelCase alias
    into the correct snake_case database column name.

    :param model: A Pydantic model class (e.g., PartnerInDB).
    :return: A dictionary where keys are either the snake_case or camelCase alias,
             and values are the final snake_case name used in the DB.
    """
    field_map = {}
    for field_name, model_field in model.model_fields.items():
        # Example:
        #   field_name = "last_name"
        #   model_field.alias = "lastName"
        field_map[field_name] = field_name
        if model_field.alias != field_name:
            field_map[model_field.alias] = field_name
    return field_map


def parse_ordering(
    ordering: Optional[str],
    field_map: dict[str, str],
    default_field: str = 'id'
) -> tuple[str, Literal['ASC', 'DESC']]:
    """
    Parse an ordering string to determine the actual DB column and direction.

    The ordering string may be:
    - A field name (e.g., "name")
    - With or without a leading '-' to denote descending order.

    :param ordering: e.g., "-name", "id"
    :param field_map: A dict from create_field_map_for_model() that maps
                      both snake_case and camelCase to the final DB column name.
    :param default_field: Fallback column name if ordering is invalid.
    :return: A tuple: (column_name_in_snake_case, direction)
             where direction is "ASC" or "DESC".
    """
    if not ordering:
        # No ordering given; use default
        return default_field, 'ASC'

    descending = ordering.startswith('-')
    if descending:
        ordering = ordering[1:]  # remove '-'

    column_name = field_map.get(ordering, default_field)

    direction: Literal['ASC', 'DESC'] = 'DESC' if descending else 'ASC'

    return column_name, direction


async def parse_optional_file(
    photo: Union[UploadFile, str, None] = None
) -> Optional[UploadFile]:
    """If empty file, return None."""
    if isinstance(photo, str) and photo == '':
        return None
    return photo
