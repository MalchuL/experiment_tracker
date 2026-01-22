from datetime import datetime
from uuid import uuid4

from domain.experiments.dto import ExperimentCreateDTO, ExperimentUpdateDTO
from domain.experiments.mapper import CreateDTOToSchemaProps, ExperimentMapper
from domain.experiments.utils import ExperimentParseResult
from models import Experiment, ExperimentStatus


class TestExperimentMapper:
    def test_experiment_parse_result_to_dto(self):
        mapper = ExperimentMapper()
        result = ExperimentParseResult(num="1", parent="root", change="seed")

        dto = mapper.experiment_parse_result_to_dto(result)

        assert dto.num == "1"
        assert dto.parent == "root"
        assert dto.change == "seed"

    def test_experiment_schema_to_dto(self):
        mapper = ExperimentMapper()
        # experiment = Experiment(
        #     id=uuid4(),
        #     project_id="123e4567-e89b-12d3-a456-426614174000",
        #     name="Experiment",
        #     description="Desc",
        #     status=ExperimentStatus.RUNNING,
        #     parent_experiment_id=None,
        #     features={"lr": 0.1},
        #     features_diff={"lr": 0.05},
        #     git_diff="diff",
        #     progress=5,
        #     color="#123456",
        #     order=1,
        #     created_at=datetime(2024, 1, 1),
        #     started_at=datetime(2024, 1, 2),
        #     completed_at=None,
        # )

        # dto = mapper.experiment_schema_to_dto(experiment)

        # assert dto.name == "Experiment"
        # assert dto.status == ExperimentStatus.RUNNING
        # assert dto.features == {"lr": 0.1}
        # assert dto.features_diff == {"lr": 0.05}
        # assert dto.progress == 5
        # assert dto.color == "#123456"
        # assert dto.order == 1

    # def test_experiment_list_schema_to_dto(self):
    #     mapper = ExperimentMapper()
    #     experiment = Experiment(
    #         id=uuid4(),
    #         project_id="123e4567-e89b-12d3-a456-426614174000",
    #         name="Experiment",
    #         description="Desc",
    #         status=ExperimentStatus.PLANNED,
    #         parent_experiment_id=None,
    #         features={},
    #         progress=0,
    #         created_at=datetime(2024, 1, 1),
    #     )

    #     dtos = mapper.experiment_list_schema_to_dto([experiment])

    #     assert len(dtos) == 1
    #     assert dtos[0].name == "Experiment"

    # def test_experiment_create_dto_to_schema_uses_parent_props(self):
    #     mapper = ExperimentMapper()
    #     dto = ExperimentCreateDTO(
    #         project_id="123e4567-e89b-12d3-a456-426614174000",
    #         name="Experiment",
    #         description="Desc",
    #         status=ExperimentStatus.PLANNED,
    #         parent_experiment_id=None,
    #         features={"lr": 0.1},
    #     )
    #     props = CreateDTOToSchemaProps(
    #         owner_id="123e4567-e89b-12d3-a456-426614174111",
    #         parent_experiment_id="123e4567-e89b-12d3-a456-426614174222",
    #     )

    #     experiment = mapper.experiment_create_dto_to_schema(dto, props)

    #     assert experiment.project_id == dto.project_id
    #     assert experiment.parent_experiment_id == props.parent_experiment_id
    #     assert experiment.features == {"lr": 0.1}

    def test_experiment_update_dto_to_update_dict(self):
        mapper = ExperimentMapper()
        dto = ExperimentUpdateDTO(
            name="Updated",
            description="Updated description",
            status=ExperimentStatus.COMPLETE,
            features={"lr": 0.2},
            git_diff="diff",
            progress=10,
            order=2,
        )

        updates = mapper.experiment_update_dto_to_update_dict(dto)

        assert updates["name"] == "Updated"
        assert updates["description"] == "Updated description"
        assert updates["status"] == ExperimentStatus.COMPLETE
        assert updates["features"] == {"lr": 0.2}
        assert updates["git_diff"] == "diff"
        assert updates["progress"] == 10
        assert updates["order"] == 2
