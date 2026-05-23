from app.domain.scalars.dto import LogScalarRequestDTO


def test_log_scalar_accepts_long_key() -> None:
    key = "s" * 2000
    dto = LogScalarRequestDTO(scalars={key: 0.5}, step=1, tags=None)
    assert key in dto.scalars
