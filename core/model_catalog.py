TAB_BANANA_1 = "banana_1"
TAB_BANANA_PRO = "banana_pro"
TAB_GPT_IMAGE = "gpt_image"

CHAT_MODELS = [
    "gemini-3.1-pro",
    "gemini-3-pro",
    "gemini-2.5-pro",
]

BANANA_1_MODELS = [
    "nano-banana-fast",
    "nano-banana"
]

BANANA_PRO_MODELS = [
    "nano-banana-2",
    "nano-banana-pro",
    "nano-banana-pro-vt",
    "nano-banana-pro-cl",
    "nano-banana-pro-vip",
    "nano-banana-pro-4k-vip"
]

GPT_IMAGE_MODELS = [
    "gpt-image-2",
]

GPT_IMAGE_SIZE_OPTIONS = [
    "auto",
    "1:1",
    "16:9",
    "9:16",
    "4:3",
    "3:4",
    "3:2",
    "2:3",
    "5:4",
    "4:5",
    "21:9",
    "9:21",
    "1:3",
    "3:1",
    "2:1",
    "1:2",
]

LEGACY_IMAGE_MODEL_ALIASES = {
    "gpt-image-1.5": "gpt-image-2",
    "sora-image": "gpt-image-2",
}

COMIC_IMAGE_MODELS = BANANA_1_MODELS + BANANA_PRO_MODELS + GPT_IMAGE_MODELS

TAB_MODELS = {
    TAB_BANANA_1: BANANA_1_MODELS,
    TAB_BANANA_PRO: BANANA_PRO_MODELS,
    TAB_GPT_IMAGE: GPT_IMAGE_MODELS,
}

NANO_IMAGE_SIZE_OPTIONS = {
    "nano-banana-2": ["1K", "2K", "4K"],
    "nano-banana-pro": ["1K", "2K", "4K"],
    "nano-banana-pro-vt": ["1K", "2K", "4K"],
    "nano-banana-pro-cl": ["1K", "2K", "4K"],
    "nano-banana-pro-vip": ["1K", "2K"],
    "nano-banana-pro-4k-vip": ["4K"],
}

VIP_MODELS = [
    "nano-banana-pro-vip",
    "nano-banana-pro-4k-vip",
    "nano-banana-pro-cl",
]

NANO_MODELS = set(BANANA_1_MODELS + BANANA_PRO_MODELS)
COMPLETION_MODELS = set(GPT_IMAGE_MODELS)
