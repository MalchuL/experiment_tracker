from typing import Any, Type
from pydantic import BaseModel


class DtoConverter[T: BaseModel]:
    def __init__(self, dto_type: Type[T]):
        self.dto_type = dto_type

    def dto_to_dict_with_dto_case(self, dto: T) -> dict:
        """Convert DTO to dict with same casing as the DTO
        Example:
            dto = ProjectCreateDTO(object_description="test")
            dict = dto_to_dict(dto)
            # dict = {"object_description": "test"}
        Args:
            dto: DTO to convert
        Returns:
            dict: Dictionary representation of the DTO
        """
        return dto.model_dump(by_alias=False, mode="json")

    def dto_to_json_dict_with_json_case(self, dto: T) -> dict:
        """Convert DTO to JSON dictionary with serialization casing
        Example:
            dto = ProjectCreateDTO(object_description="test")
            json_dict = dto_to_json_dict(dto)
            # json_dict = {"objectDescription": "test"}
        Args:
            dto: DTO to convert
        Returns:
            dict: JSON dictionary representation of the DTO
        """
        return dto.model_dump(by_alias=True, mode="json")

    def dict_with_json_case_to_dto(self, data: dict | Any) -> T:
        """Convert dict to DTO with any casing
        This method will convert the dictionary to the DTO with the same casing as the DTO.
        Example:
            data = {"objectDescription": "test"}
            dto = dict_to_dto(data, ProjectCreateDTO)
            # dto = ProjectCreateDTO(object_description="test")
        Args:
            data: Dictionary to convert
            dto_type: Type of DTO to convert to
        Returns:
            DTO: DTO representation of the dictionary
        """
        return self.dto_type.model_validate(data)

    def dto_to_partial_dict_with_dto_case(self, dto: T) -> dict:
        """Convert DTO to partial dict with same casing as the DTO
        Example:
            dto = ProjectCreateDTO(object_description="test")
            dict = dto_to_partial_dict(dto)
            # dict = {"object_description": "test"}
        Args:
            dto: DTO to convert
        Returns:
            dict: Partial dictionary representation of the DTO
        """
        return dto.model_dump(by_alias=False, mode="json", exclude_unset=True)
