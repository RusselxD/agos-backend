import pytest
from pydantic import ValidationError

from app.models import SensorConfig


def test_sensor_config_accepts_warning_below_critical():
    config = SensorConfig(
        installation_height=200,
        warning_threshold=70,
        critical_threshold=90,
    )

    assert config.warning_threshold == 70
    assert config.critical_threshold == 90


@pytest.mark.parametrize(
    ("warning_threshold", "critical_threshold"),
    [
        (90, 70),
        (70, 70),
    ],
)
def test_sensor_config_rejects_warning_not_below_critical(
    warning_threshold,
    critical_threshold,
):
    with pytest.raises(
        ValidationError,
        match="warning_threshold must be lower than critical_threshold",
    ):
        SensorConfig(
            installation_height=200,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )


def test_sensor_config_rejects_non_numeric_threshold():
    with pytest.raises(ValidationError):
        SensorConfig(
            installation_height=200,
            warning_threshold="not-a-number",
            critical_threshold=90,
        )
