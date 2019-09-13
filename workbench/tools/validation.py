import datetime as dt
from functools import wraps

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.translation import gettext as _


def monday(day=None):
    day = day or dt.date.today()
    return day - dt.timedelta(days=day.weekday())


def raise_if_errors(errors, exclude=None):
    if errors:
        if set(exclude or ()) & errors.keys():
            raise ValidationError(", ".join(str(e) for e in errors.values()))
        raise ValidationError(errors)


def filter_form(form_class):
    def decorator(view):
        @wraps(view)
        def inner(request, *args, **kwargs):
            form = form_class(request.GET)
            if not form.is_valid():
                messages.warning(request, _("Form was invalid."))
                return redirect(".")
            return view(request, form, *args, **kwargs)

        return inner

    return decorator
