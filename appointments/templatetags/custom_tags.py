from django import template

register = template.Library()


@register.filter
def duration(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    hours_str = ""
    if hours == 1:
        hours_str = f'1 hora'
    elif hours > 1:
        hours_str = f'{hours} horas'

    minutes_str = ""
    if minutes == 1:
        minutes_str = f'1 minuto'
    elif minutes > 1:
        minutes_str = f'{minutes} minutos'

    return f'{hours_str} {minutes_str}'


@register.filter
def price(value):
    return f'${value:,}'
