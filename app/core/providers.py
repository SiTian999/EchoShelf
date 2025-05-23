import os


def get_provider(name: str):
    MODEL_PROVIDERS = {
        "deepseek": {
            "base_url": os.getenv(
                "DEEPSEEK_API_BASE",
                "https://api.deepseek.com/v1"
            ),
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "model": "deepseek-chat"
        },
        "qwen": {
            "base_url": os.getenv(
                "QWEN_API_BASE",
                "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            "api_key": os.getenv("QWEN_API_KEY"),
            "model": "qwen-max-latest"
        }
    }
    return MODEL_PROVIDERS.get(name, MODEL_PROVIDERS["deepseek"])
