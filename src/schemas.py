from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class IDModel(BaseModel):
    id: Annotated[
        int,
        Field(description='Instance ID')
    ]


class ConfiguredModel(BaseModel):
    """
    Allows CamelCase as an input as well as default snake_case
    and allows to populate model attributes from ORM objects or dictionaries
    """
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class CreatedUpdatedAt(ConfiguredModel):
    created_at: Annotated[
        datetime,
        Field(
            ...,
            title='Created at',
        )
    ]
    updated_at: Annotated[
        datetime,
        Field(
            ...,
            title='Updated at',
        )
    ]
