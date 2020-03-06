import datetime as dt
from decimal import Decimal

from django.utils.formats import date_format
from django.utils.timezone import localtime


H1 = Decimal("0.0")
H2 = Decimal("0.00")


def local_date_format(dttm, fmt=None):
    if not dttm:
        return ""
    if hasattr(dttm, "astimezone"):
        dttm = localtime(dttm)
    return date_format(
        dttm, fmt or ("d.m.Y H:i" if isinstance(dttm, dt.datetime) else "d.m.Y")
    )


def _fmt(*, fmt, value, exp, plus_sign=False):
    value = value.quantize(exp) if value else exp
    value = value if value != 0 else exp  # Avoid -0.0
    return fmt.format("+" if plus_sign and value > 0 else "", value).replace(",", "’")


def currency(value, plus_sign=False):
    return _fmt(fmt="{}{:,.2f}", value=value, exp=H2, plus_sign=plus_sign)


def days(value, plus_sign=False):
    return _fmt(fmt="{}{:,.2f}d", value=value, exp=H2, plus_sign=plus_sign)


def hours(value, plus_sign=False):
    return _fmt(fmt="{}{:,.1f}h", value=value, exp=H1, plus_sign=plus_sign)


def in_days(days):
    return dt.date.today() + dt.timedelta(days=days)
