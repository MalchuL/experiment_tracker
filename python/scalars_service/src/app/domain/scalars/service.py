from collections import defaultdict
from app.domain.scalars.dto import (
    ExperimentsScalarsPointsResultDTO,
    ScalarsPointsResultDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS, ProjectTableColumns
import asyncpg
import json


def _check_is_none(value: any) -> bool:
    return value is None or value == "null" or value == "None"


class ScalarsService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    def _split_scalars_by_experiment_id(
        self, scalars: list[dict], return_tags: bool = False
    ):
        result_scalars = defaultdict(list)
        result_tags = defaultdict(list)
        for scalar in scalars:
            result_scalars[scalar[ProjectTableColumns.EXPERIMENT_ID.value]].append(
                (
                    scalar[ProjectTableColumns.STEP.value],
                    scalar[ProjectTableColumns.VALUE.value],
                )
            )
            print(
                scalar[ProjectTableColumns.TAGS.value],
                type(scalar[ProjectTableColumns.TAGS.value]),
            )
            if return_tags and not _check_is_none(
                scalar[ProjectTableColumns.TAGS.value]
            ):
                result_tags[scalar[ProjectTableColumns.EXPERIMENT_ID.value]].append(
                    (
                        scalar[ProjectTableColumns.STEP.value],
                        json.loads(scalar[ProjectTableColumns.TAGS.value]),
                    )
                )

        return result_scalars, result_tags

    async def get_scalars(
        self,
        project_id: str,
        experiment_id: str,
        max_points: int | None = None,
        return_tags: bool = False,
    ):
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        select_statement = SCALARS_DB_UTILS.build_select_statement_with_experiment_id(
            table_name, experiment_id
        )
        scalars = await self.conn.fetch(select_statement)
        result_scalars, result_tags = self._split_scalars_by_experiment_id(
            scalars, return_tags
        )

        result = []
        unique_tags: set[str] = set()
        for experiment_id, scalars in result_scalars.items():
            print(result_tags[experiment_id])
            result_item = ExperimentsScalarsPointsResultDTO(
                experiment_id=experiment_id,
                scalars=scalars,
                tags=result_tags[experiment_id],
            )
            result.append(result_item)
            print(result_tags[experiment_id])
            for _, tags in result_tags[experiment_id]:
                unique_tags.update(tags)

        return ScalarsPointsResultDTO(data=result, tags=list(unique_tags))
