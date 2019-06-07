from .kodiutils import get_setting_as_bool

LANGUAGES = [
    "ta", "kn", "pa", "bn", "en", "ml", "mr", "hr", "gu", "te", "hi"
]

DEFAULT_LANGUAGES = 'en,ta'


def get_languages():
    return ','.join([
        lang for lang in LANGUAGES if get_setting_as_bool(lang)
    ]) or DEFAULT_LANGUAGES


def is_debug():
    return get_setting_as_bool('debug')