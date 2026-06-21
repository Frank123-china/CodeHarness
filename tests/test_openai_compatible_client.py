import pytest

from codeharness.llm import LLMClientError, OpenAICompatibleClient


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class _Chat:
    def __init__(self, completions):
        self.completions = completions


class _SDKClient:
    def __init__(self, completions):
        self.chat = _Chat(completions)


def test_constructor_passes_settings_to_sdk_factory() -> None:
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return _SDKClient(_Completions(_Response("ok")))

    OpenAICompatibleClient(
        model="test-model",
        api_key="secret-key",
        base_url="https://example.test/v1",
        timeout_seconds=12,
        sdk_client_factory=factory,
    )

    assert captured == {
        "api_key": "secret-key",
        "base_url": "https://example.test/v1",
        "timeout": 12,
        "max_retries": 0,
    }


def test_prompt_is_wrapped_as_user_message() -> None:
    completions = _Completions(_Response("answer"))
    client = OpenAICompatibleClient(
        model="test-model",
        api_key="secret-key",
        base_url="https://example.test/v1",
        sdk_client=_SDKClient(completions),
    )

    response = client.complete("hello prompt")

    assert response == "answer"
    assert completions.calls == [
        {
            "model": "test-model",
            "messages": [{"role": "user", "content": "hello prompt"}],
        }
    ]


def test_empty_response_raises_llm_client_error() -> None:
    client = OpenAICompatibleClient(
        model="test-model",
        api_key="secret-key",
        base_url="https://example.test/v1",
        sdk_client=_SDKClient(_Completions(_Response(""))),
    )

    with pytest.raises(LLMClientError, match="did not contain text"):
        client.complete("prompt")


def test_sdk_exception_becomes_llm_client_error_without_api_key() -> None:
    client = OpenAICompatibleClient(
        model="test-model",
        api_key="secret-key",
        base_url="https://example.test/v1",
        sdk_client=_SDKClient(_Completions(error=RuntimeError("bad secret-key failure"))),
    )

    with pytest.raises(LLMClientError) as exc_info:
        client.complete("prompt")

    message = str(exc_info.value)
    assert "bad [redacted] failure" in message
    assert "secret-key" not in message


def test_factory_exception_becomes_llm_client_error_without_api_key() -> None:
    def factory(**kwargs):
        raise RuntimeError("cannot use secret-key")

    with pytest.raises(LLMClientError) as exc_info:
        OpenAICompatibleClient(
            model="test-model",
            api_key="secret-key",
            base_url="https://example.test/v1",
            sdk_client_factory=factory,
        )

    assert "secret-key" not in str(exc_info.value)
