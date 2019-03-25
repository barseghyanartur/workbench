from datetime import date

from django import forms
from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from workbench.accounts.models import User
from workbench.contacts.forms import PostalAddressSelectionForm
from workbench.contacts.models import Organization, Person
from workbench.invoices.models import Invoice, RecurringInvoice, Service
from workbench.logbook.models import LoggedCost, LoggedHours
from workbench.services.models import ServiceType
from workbench.tools.formats import currency, hours, local_date_format
from workbench.tools.forms import ModelForm, Picker, Textarea, WarningsForm
from workbench.tools.models import Z


class InvoiceSearchForm(forms.Form):
    s = forms.ChoiceField(
        choices=(
            ("all", _("All states")),
            ("", _("Open")),
            (_("Exact"), Invoice.STATUS_CHOICES),
        ),
        required=False,
        widget=forms.Select(attrs={"class": "custom-select"}),
    )
    org = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False,
        widget=Picker(model=Organization),
    )
    owned_by = forms.TypedChoiceField(
        label=_("owned by"),
        coerce=int,
        required=False,
        widget=forms.Select(attrs={"class": "custom-select"}),
    )
    dunning = forms.BooleanField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owned_by"].choices = User.objects.choices(collapse_inactive=True)

    def filter(self, queryset):
        data = self.cleaned_data
        if data.get("s") == "all":
            pass
        elif data.get("s") == "":
            queryset = queryset.filter(
                status__in=(Invoice.IN_PREPARATION, Invoice.SENT, Invoice.REMINDED)
            )
        elif data.get("s"):
            queryset = queryset.filter(status=data.get("s"))
        if data.get("org"):
            queryset = queryset.filter(customer=data.get("org"))
        if data.get("owned_by") == 0:
            queryset = queryset.filter(owned_by__is_active=False)
        elif data.get("owned_by"):
            queryset = queryset.filter(owned_by=data.get("owned_by"))
        if data.get("dunning"):
            queryset = queryset.filter(
                status__in=(Invoice.SENT, Invoice.REMINDED), due_on__lte=date.today()
            ).order_by("due_on")

        return queryset.select_related(
            "customer", "contact__organization", "owned_by", "project__owned_by"
        )


class InvoiceForm(WarningsForm, PostalAddressSelectionForm):
    user_fields = default_to_current_user = ("owned_by",)

    class Meta:
        model = Invoice
        fields = (
            "customer",
            "contact",
            "invoiced_on",
            "due_on",
            "title",
            "description",
            "owned_by",
            "status",
            "closed_on",
            "postal_address",
            "type",
            "subtotal",
            "third_party_costs",
            "discount",
            "liable_to_vat",
        )
        widgets = {
            "customer": Picker(model=Organization),
            "contact": Picker(model=Person),
            "status": forms.RadioSelect,
            "description": Textarea,
            "postal_address": Textarea,
            "type": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["type"].choices = Invoice.TYPE_CHOICES
        self.fields["type"].disabled = True

        if self.instance.project:
            del self.fields["customer"]

        if self.instance.type == self.instance.DOWN_PAYMENT:
            self.fields["subtotal"].label = _("Down payment")

        elif self.instance.type == self.instance.SERVICES:
            self.fields["subtotal"].disabled = True
            self.fields["third_party_costs"].disabled = True
            self.fields["subtotal"].help_text = _("Calculated from invoice services.")
            self.fields["third_party_costs"].help_text = _(
                "Calculated from invoice services."
            )

        if self.instance.type != Invoice.DOWN_PAYMENT and self.instance.project_id:
            eligible_down_payment_invoices = Invoice.objects.valid().filter(
                Q(project=self.instance.project),
                Q(type=Invoice.DOWN_PAYMENT),
                Q(down_payment_applied_to__isnull=True)
                | Q(down_payment_applied_to=self.instance),
            )
            if eligible_down_payment_invoices:
                self.fields["apply_down_payment"] = forms.ModelMultipleChoiceField(
                    label=_("Apply down payment invoices"),
                    queryset=eligible_down_payment_invoices,
                    widget=forms.CheckboxSelectMultiple,
                    required=False,
                    initial=Invoice.objects.filter(
                        down_payment_applied_to=self.instance
                    ).values_list("id", flat=True)
                    if self.instance.pk
                    else [],
                )
                self.fields["apply_down_payment"].choices = [
                    (
                        invoice.id,
                        format_html(
                            "{}<br/>{}, {}",
                            invoice.__html__(),
                            _("%s excl. tax") % currency(invoice.total_excl_tax),
                            invoice.pretty_status(),
                        ),
                    )
                    for invoice in eligible_down_payment_invoices
                ]

        self.order_fields(
            field
            for field in list(self.fields)
            if field not in {"discount", "apply_down_payment", "liable_to_vat"}
        )

        if not self.instance.postal_address:
            self.add_postal_address_selection(person=self.instance.contact)

    def _is_status_unexpected(self, to_status):
        if not to_status:
            return False

        from_status = self.instance._orig_status

        if from_status == to_status:
            return False
        if from_status > to_status or from_status >= Invoice.PAID:
            return True
        return False

    def clean(self):
        data = super().clean()
        s_dict = dict(Invoice.STATUS_CHOICES)

        if self.instance.project and data.get("contact"):
            if data["contact"].organization != self.instance.project.customer:
                raise forms.ValidationError(
                    {
                        "contact": _(
                            "Selected contact does not belong to project's"
                            " organization, %(organization)s."
                        )
                        % {"organization": self.instance.project.customer}
                    }
                )

        if self.instance._orig_status < self.instance.SENT:
            invoiced_on = data.get("invoiced_on")
            if invoiced_on and invoiced_on < date.today():
                self.add_warning(
                    _(
                        "Invoice date is in the past, but invoice is still"
                        " in preparation. Are you sure you do not want to"
                        " set the invoice date to today?"
                    )
                )

        if self.instance.status > self.instance.IN_PREPARATION:
            if set(self.changed_data) - {"status", "closed_on"}:
                self.add_warning(
                    _(
                        "You are attempting to change %(fields)s."
                        " I am trying to prevent unintentional changes to"
                        " anything but the status and closed on fields."
                        " Are you sure?"
                    )
                    % {
                        "fields": ", ".join(
                            "'%s'" % self.fields[field].label
                            for field in self.changed_data
                        )
                    }
                )

        if self._is_status_unexpected(data.get("status")):
            self.add_warning(
                _("Moving status from '%(from)s' to '%(to)s'. Are you sure?")
                % {
                    "from": s_dict[self.instance._orig_status],
                    "to": s_dict[data["status"]],
                }
            )

        if data.get("status", 0) >= Invoice.PAID and not data.get("closed_on"):
            data["closed_on"] = date.today()

        if self.instance.closed_on and data.get("status", 99) < Invoice.PAID:
            if self.should_ignore_warnings():
                self.instance.closed_on = None
            else:
                self.add_warning(
                    _(
                        "You are attempting to set status to '%(to)s',"
                        " but the invoice has already been closed on %(closed)s."
                        " Are you sure?"
                    )
                    % {
                        "to": s_dict[data["status"]],
                        "closed": local_date_format(self.instance.closed_on, "d.m.Y"),
                    }
                )

        if not data.get("contact"):
            self.add_warning(_("No contact selected."))
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.type in (instance.FIXED, instance.DOWN_PAYMENT):
            instance.subtotal = self.cleaned_data["subtotal"]
            instance.down_payment_total = Z

        if "apply_down_payment" in self.cleaned_data:
            if not instance.pk:
                instance.save()

            instance.down_payment_invoices.set(
                self.cleaned_data.get("apply_down_payment")
            )
            instance.down_payment_total = sum(
                (
                    invoice.total_excl_tax
                    for invoice in self.cleaned_data.get("apply_down_payment")
                ),
                Z,
            )

        if commit:
            instance.save()
        return instance


class CreateProjectInvoiceForm(InvoiceForm):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project", None)
        if not kwargs.get("instance"):
            kwargs["instance"] = Invoice(
                customer=self.project.customer,
                contact=self.project.contact,
                project=self.project,
                title=self.project.title,
                description=self.project.description,
                type=kwargs["request"].GET.get("type"),
            )

        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            # Hide those fields when creating invoices
            del self.fields["status"]
            del self.fields["closed_on"]

            invoice_type = self.request.GET.get("type")
            self.fields["type"].initial = self.instance.type = invoice_type

            if invoice_type == "services":
                self.add_services_field()

    def add_services_field(self):
        source = self.request.GET.get("source")
        if source == "logbook":

            def amount(service):
                if not service.pk:
                    return format_html(
                        '{} <small class="bg-warning px-1">{}</small>',
                        currency(service.service_cost),
                        _("%s logged but not bound to a service.")
                        % currency(service.logged_cost),
                    )
                elif service.effort_rate is not None:
                    return currency(
                        service.effort_rate * service.logged_hours + service.logged_cost
                    )
                elif service.logged_hours:
                    return format_html(
                        '{} <small class="bg-warning px-1">{}</small>',
                        currency(service.service_cost),
                        _("%s logged but no hourly rate defined.")
                        % hours(service.logged_hours),
                    )
                return currency(service.logged_cost)

        else:

            def amount(service):
                return currency(service.service_cost)

        choices = []
        for offer, services in self.project.grouped_services:
            choices.append(
                (
                    format_html(
                        "<u>{}</u><br>"
                        '<div class="form-check">'
                        '<input type="checkbox" data-toggle-following>'
                        "{}"
                        "</div>",
                        offer if offer else _("Not offered yet"),
                        _("Choose all"),
                    ),
                    [
                        (
                            service.id,
                            format_html(
                                '<div class="mb-2"><strong>{}</strong>'
                                "<br>{}{}</div>",
                                service.title,
                                format_html("{}<br>", service.description)
                                if service.description
                                else "",
                                amount(service),
                            ),
                        )
                        for service in services
                    ],
                )
            )
        self.fields["selected_services"] = forms.MultipleChoiceField(
            choices=choices,
            label=_("services"),
            widget=forms.CheckboxSelectMultiple(attrs={"size": 30}),
        )

    def save(self):
        if self.request.GET.get("type") != "services":
            return super().save()

        instance = super().save(commit=False)
        services = self.project.services.filter(
            id__in=self.cleaned_data["selected_services"]
        )
        if self.request.GET.get("source") == "logbook":
            instance.create_services_from_logbook(services)
        else:
            instance.create_services_from_offer(services)
        return instance


class CreatePersonInvoiceForm(PostalAddressSelectionForm):
    user_fields = default_to_current_user = ("owned_by",)
    type = forms.ChoiceField(
        label=_("type"),
        choices=Invoice.TYPE_CHOICES,
        initial=Invoice.FIXED,
        disabled=True,
        widget=forms.RadioSelect,
        help_text=_("Other invoice types must be created directly on a project."),
    )

    class Meta:
        model = Invoice
        fields = (
            "customer",
            "contact",
            "invoiced_on",
            "due_on",
            "title",
            "description",
            "owned_by",
            "postal_address",
            "subtotal",
            "discount",
            "liable_to_vat",
        )
        widgets = {
            "customer": Picker(model=Organization),
            "contact": Picker(model=Person),
            "description": Textarea,
            "postal_address": Textarea,
        }

    def __init__(self, *args, **kwargs):
        request = kwargs["request"]
        initial = kwargs.setdefault("initial", {})
        initial.update({"subtotal": None})  # Invalid -- force input.

        contact = None
        customer = None
        self.pre_form = False

        if request.GET.get("contact"):
            try:
                contact = Person.objects.get(pk=request.GET.get("contact"))
            except (Person.DoesNotExist, TypeError, ValueError):
                pass
            else:
                initial.update({"customer": contact.organization, "contact": contact})

        elif request.GET.get("customer"):
            try:
                customer = Organization.objects.get(pk=request.GET.get("customer"))
            except (Organization.DoesNotExist, TypeError, ValueError):
                pass
            else:
                initial.update({"customer": customer})

        elif request.GET.get("copy_invoice"):
            try:
                invoice = Invoice.objects.get(pk=request.GET.get("copy_invoice"))
            except (Invoice.DoesNotExist, TypeError, ValueError):
                pass
            else:
                initial.update(
                    {
                        "customer": invoice.customer_id,
                        "contact": invoice.contact_id,
                        "title": invoice.title,
                        "description": invoice.description,
                        "postal_address": invoice.postal_address,
                        "type": invoice.type,
                        "subtotal": invoice.subtotal,
                        "discount": invoice.discount,
                        "liable_to_vat": invoice.liable_to_vat,
                        "tax_rate": invoice.tax_rate,
                        "total": invoice.total,
                    }
                )
        else:
            self.pre_form = True

        super().__init__(*args, **kwargs)

        self.instance.type = Invoice.FIXED

        if self.pre_form:
            for field in list(self.fields):
                if field not in {"customer", "contact"}:
                    self.fields.pop(field)
        elif contact:
            self.add_postal_address_selection(person=contact)
        elif customer:
            self.add_postal_address_selection(organization=customer)


class InvoiceDeleteForm(ModelForm, WarningsForm):
    class Meta:
        model = Invoice
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.status > Invoice.IN_PREPARATION:
            # Should not happen but if it does, fail validation here
            self.fields["_block"] = forms.BooleanField(disabled=True, required=True)
            return

        if (
            LoggedHours.objects.filter(invoice_service__invoice=self.instance).exists()
            or LoggedCost.objects.filter(
                invoice_service__invoice=self.instance
            ).exists()
        ):
            self.add_warning(
                _(
                    "Logged services are linked with this invoice."
                    " They will be released when deleting this invoice."
                )
            )

    def delete(self):
        LoggedHours.objects.filter(invoice_service__invoice=self.instance).update(
            invoice_service=None, archived_at=None
        )
        LoggedCost.objects.filter(invoice_service__invoice=self.instance).update(
            invoice_service=None, archived_at=None
        )
        self.instance.delete()


class ServiceForm(ModelForm):
    service_type = forms.ModelChoiceField(
        ServiceType.objects.all(),
        label=ServiceType._meta.verbose_name,
        required=False,
        help_text=_("Optional, but useful for quickly filling the fields below."),
    )

    class Meta:
        model = Service
        fields = [
            "title",
            "description",
            "effort_type",
            "effort_hours",
            "effort_rate",
            "cost",
            "third_party_costs",
        ]
        widgets = {"description": Textarea}

    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop("invoice", None)
        if not self.invoice:
            self.invoice = kwargs["instance"].invoice
        super().__init__(*args, **kwargs)
        self.instance.invoice = self.invoice


class RecurringInvoiceSearchForm(forms.Form):
    s = forms.ChoiceField(
        choices=(("all", _("All states")), ("", _("Open")), ("closed", _("Closed"))),
        required=False,
        widget=forms.Select(attrs={"class": "custom-select"}),
    )
    org = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False,
        widget=Picker(model=Organization),
    )
    owned_by = forms.TypedChoiceField(
        label=_("owned by"),
        coerce=int,
        required=False,
        widget=forms.Select(attrs={"class": "custom-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owned_by"].choices = User.objects.choices(collapse_inactive=True)

    def filter(self, queryset):
        data = self.cleaned_data
        if data.get("s") == "":
            queryset = queryset.filter(
                Q(ends_on__isnull=True) | Q(ends_on__gte=date.today())
            )
        elif data.get("s") == "closed":
            queryset = queryset.filter(
                Q(ends_on__isnull=False) & Q(ends_on__lt=date.today())
            )
        if data.get("org"):
            queryset = queryset.filter(customer=data.get("org"))
        if data.get("owned_by") == 0:
            queryset = queryset.filter(owned_by__is_active=False)
        elif data.get("owned_by"):
            queryset = queryset.filter(owned_by=data.get("owned_by"))

        return queryset.select_related("customer", "contact__organization", "owned_by")


class CreateRecurringInvoiceForm(ModelForm):
    user_fields = default_to_current_user = ("owned_by",)

    class Meta:
        model = RecurringInvoice
        fields = (
            "customer",
            "contact",
            "title",
            "description",
            "owned_by",
            "starts_on",
            "periodicity",
            "subtotal",
            "discount",
            "liable_to_vat",
            "third_party_costs",
        )
        widgets = {
            "customer": Picker(model=Organization),
            "contact": Picker(model=Person),
            "description": Textarea,
            "periodicity": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["periodicity"].choices = RecurringInvoice.PERIODICITY_CHOICES


class RecurringInvoiceForm(WarningsForm, PostalAddressSelectionForm):
    user_fields = default_to_current_user = ("owned_by",)

    class Meta:
        model = RecurringInvoice
        fields = (
            "customer",
            "contact",
            "title",
            "description",
            "owned_by",
            "postal_address",
            "starts_on",
            "ends_on",
            "periodicity",
            "next_period_starts_on",
            "subtotal",
            "discount",
            "liable_to_vat",
            "third_party_costs",
        )
        widgets = {
            "customer": Picker(model=Organization),
            "contact": Picker(model=Person),
            "description": Textarea,
            "postal_address": Textarea,
            "periodicity": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["periodicity"].choices = RecurringInvoice.PERIODICITY_CHOICES
        self.fields["next_period_starts_on"].disabled = True

        if not self.instance.postal_address:
            self.add_postal_address_selection(person=self.instance.contact)

    def clean(self):
        data = super().clean()

        if not data.get("contact"):
            self.add_warning(_("No contact selected."))
        return data
