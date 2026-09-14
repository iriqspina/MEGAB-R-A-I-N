def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def composite_over(fg_hex: str, bg_rgb: tuple[int, int, int], alpha_percent: float) -> tuple[int, int, int]:
    fg = hex_to_rgb(fg_hex)
    alpha = alpha_percent / 100.0
    return tuple(round(fg[i] * alpha + bg_rgb[i] * (1 - alpha)) for i in range(3))


def _linearize(channel_0_255: int) -> float:
    c = channel_0_255 / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]) -> float:
    lum_a, lum_b = relative_luminance(rgb_a), relative_luminance(rgb_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def worst_case_contrast(fg_hex: str, panel_bg_hex: str, alpha_percent: float) -> float:
    """Pior contraste do texto contra o painel translucido nos dois extremos
    de fundo real (branco puro e preto puro) — o widget nao controla o que
    fica atras dele."""
    fg = hex_to_rgb(fg_hex)
    over_white = composite_over(panel_bg_hex, WHITE, alpha_percent)
    over_black = composite_over(panel_bg_hex, BLACK, alpha_percent)
    return min(contrast_ratio(fg, over_white), contrast_ratio(fg, over_black))
