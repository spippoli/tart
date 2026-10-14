"""The text search configuration of the Content language (Discovery spec, Search)."""

# PostgreSQL's built-in stemming configurations, by ISO 639-1 code.
_CONFIGURATIONS = {
    "ar": "arabic",
    "ca": "catalan",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
    "es": "spanish",
    "eu": "basque",
    "fi": "finnish",
    "fr": "french",
    "ga": "irish",
    "hi": "hindi",
    "hu": "hungarian",
    "hy": "armenian",
    "id": "indonesian",
    "it": "italian",
    "lt": "lithuanian",
    "ne": "nepali",
    "nl": "dutch",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sr": "serbian",
    "sv": "swedish",
    "ta": "tamil",
    "tr": "turkish",
    "yi": "yiddish",
}


def text_search_configuration(content_language: str) -> str:
    """`italian` for `it`, and so on; `simple` for a language PostgreSQL has no stemmer for.

    The UI language never reaches here: search reads the Content language only.
    """
    return _CONFIGURATIONS.get(content_language, "simple")
