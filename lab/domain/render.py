"""{{PLACEHOLDER}} substitution shared by every target's nginx config."""
import re

_UNFILLED = re.compile(r"\{\{[^{}]*\}\}")


def render(template: str, mapping: dict[str, str]) -> str:
    """Replace ``{{KEY}}`` for every key in *mapping*.

    Raises ValueError if any ``{{`` remains, so an incomplete nginx config
    can never be written out and silently break the target.
    """
    out = template
    for key, value in mapping.items():
        out = out.replace("{{%s}}" % key, value)
    if "{{" in out:
        leftover = _UNFILLED.findall(out)
        raise ValueError("unfilled placeholder: " + (", ".join(leftover)
                                                     if leftover else
                                                     out[out.index("{{"):].splitlines()[0]))
    return out
