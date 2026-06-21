from codeharness.config import CodeHarnessConfig


def test_config_defaults_load() -> None:
    config = CodeHarnessConfig.from_env({})

    assert config.model_name == "gpt-4.1-mini"
    assert config.api_key is None
    assert config.base_url == "https://api.openai.com/v1"
    assert config.max_steps == 8
    assert config.command_timeout == 30
    assert config.api_key_configured is False


def test_config_reads_environment_values() -> None:
    config = CodeHarnessConfig.from_env(
        {
            "CODEHARNESS_MODEL": "local-test-model",
            "CODEHARNESS_API_KEY": "test-key",
            "CODEHARNESS_BASE_URL": "http://localhost:8000/v1",
            "CODEHARNESS_MAX_STEPS": "3",
            "CODEHARNESS_COMMAND_TIMEOUT": "12",
        }
    )

    assert config.model_name == "local-test-model"
    assert config.api_key == "test-key"
    assert config.base_url == "http://localhost:8000/v1"
    assert config.max_steps == 3
    assert config.command_timeout == 12
    assert config.api_key_configured is True
