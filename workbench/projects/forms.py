from collections import OrderedDict

from django import forms, http
from django.forms.models import inlineformset_factory
from django.utils.translation import ugettext_lazy as _

from workbench.accounts.models import User
from workbench.contacts.models import Organization, Person
from workbench.projects.models import Project, Service, Effort, Cost
from workbench.tools.forms import ModelForm, Textarea, Picker


class ProjectSearchForm(forms.Form):
    s = forms.ChoiceField(
        choices=(
            ("", _("All states")),
            ("open", _("Open")),
            (_("Exact"), Project.STATUS_CHOICES),
        ),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    owned_by = forms.TypedChoiceField(
        label=_("owned by"),
        coerce=int,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owned_by"].choices = [
            ("", _("All users")),
            (0, _("Owned by inactive users")),
            (
                _("Active"),
                [
                    (u.id, u.get_full_name())
                    for u in User.objects.filter(is_active=True)
                ],
            ),
        ]

    def filter(self, queryset):
        data = self.cleaned_data
        if data.get("s") == "open":
            queryset = queryset.filter(status__lte=Project.WORK_IN_PROGRESS)
        elif data.get("s"):
            queryset = queryset.filter(status=data.get("s"))
        if data.get("owned_by") == 0:
            queryset = queryset.filter(owned_by__is_active=False)
        elif data.get("owned_by"):
            queryset = queryset.filter(owned_by=data.get("owned_by"))

        return queryset

    def response(self, request):
        if "s" not in request.GET:
            return http.HttpResponseRedirect("?s=open")


class ProjectForm(ModelForm):
    user_fields = default_to_current_user = ("owned_by",)

    class Meta:
        model = Project
        fields = (
            "customer",
            "contact",
            "title",
            "description",
            "owned_by",
            "status",
            "invoicing",
            "maintenance",
        )
        widgets = {
            "customer": Picker(model=Organization),
            "contact": Picker(model=Person),
            "status": forms.RadioSelect,
        }


class ServiceForm(ModelForm):
    class Meta:
        model = Service
        fields = ("title", "description")
        widgets = {"description": Textarea()}

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        kwargs.pop("request")
        self.formsets = (
            OrderedDict(
                (
                    ("efforts", EffortFormset(*args, **kwargs)),
                    ("costs", CostFormset(*args, **kwargs)),
                )
            )
            if self.instance.pk
            else OrderedDict()
        )

        if self.project:
            self.instance.project = self.project

    def is_valid(self):
        return all(
            [super().is_valid()]
            + [formset.is_valid() for formset in self.formsets.values()]
        )

    def save(self):
        instance = super().save(commit=False)
        for formset in self.formsets.values():
            formset.save()
        instance.save()
        return instance


EffortFormset = inlineformset_factory(
    Service, Effort, fields=("service_type", "hours"), extra=0
)

CostFormset = inlineformset_factory(Service, Cost, fields=("title", "cost"), extra=0)
