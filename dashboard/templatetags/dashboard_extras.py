from django import template

register = template.Library()


@register.filter(name="get_item")
def get_item(value, key):
    """Safely fetch an item from dict-like objects in templates."""
    if value is None:
        return None

    try:
        return value.get(key)
    except AttributeError:
        try:
            return value[key]
        except (TypeError, KeyError, IndexError):
            return None
