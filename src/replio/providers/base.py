class BaseProvider:
    def __init__(self, base_url: str = '', api_key: str = '',
                 model: str = '', temperature: float = 0.7,
                 max_tokens: int = 2048):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: list[dict], stream: bool = True):
        raise NotImplementedError

    def chat_nonstreaming(self, messages: list[dict],
                          tools: list[dict] | None = None) -> dict:
        raise NotImplementedError

    def list_models(self) -> list[str]:
        raise NotImplementedError
