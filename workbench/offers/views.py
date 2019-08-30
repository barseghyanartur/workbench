from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from workbench.generic import DetailView
from workbench.offers.models import Offer
from workbench.projects.forms import ProjectAutocompleteForm
from workbench.projects.models import Project
from workbench.tools.pdf import pdf_response


class OfferPDFView(DetailView):
    model = Offer

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        pdf, response = pdf_response(self.object.code, as_attachment=False)

        pdf.init_letter()
        pdf.process_offer(self.object)
        pdf.generate()

        return response


class ProjectOfferPDFView(DetailView):
    model = Project

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        offers = list(self.object.offers.order_by("_code"))

        if not offers:
            messages.error(request, _("No offers in project."))
            return redirect(self.object)

        pdf, response = pdf_response(self.object.code, as_attachment=False)
        pdf.offers_pdf(project=self.object, offers=offers)

        return response


def copy_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    form = ProjectAutocompleteForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        new = offer.copy_to(project=form.cleaned_data["project"], owned_by=request.user)
        return JsonResponse({"redirect": new.get_absolute_url()}, status=299)
    return render(
        request,
        "projects/select_project.html",
        {"form": form, "title": _("Copy %s to project") % offer},
    )
