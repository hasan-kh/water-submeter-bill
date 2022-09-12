from django import template
from persiantools.digits import en_to_fa


register = template.Library()

@register.filter
def topersian(value):
    """
    :param value: english digits
    :return: persian digits
    """
    return en_to_fa(str(value))
