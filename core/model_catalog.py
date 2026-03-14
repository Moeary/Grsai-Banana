TAB_BANANA_1 = "banana_1"
TAB_BANANA_PRO = "banana_pro"
TAB_GPT_IMAGE = "gpt_image"

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
    "gpt-image-1.5",
    "sora-image"
]

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
