from django.urls import path

from workbench import generic
from workbench.planning.forms import (
    PlannedWorkForm,
    PlannedWorkSearchForm,
    PlanningRequestForm,
    PlanningRequestSearchForm,
)
from workbench.planning.models import PlannedWork, PlanningRequest


urlpatterns = [
    # Requests
    path(
        "requests/",
        generic.ListView.as_view(
            model=PlanningRequest, search_form_class=PlanningRequestSearchForm
        ),
        name="planning_planningrequest_list",
    ),
    path(
        "requests/<int:pk>/",
        generic.DetailView.as_view(model=PlanningRequest),
        name="planning_planningrequest_detail",
    ),
    path(
        "requests/create/",
        generic.CreateView.as_view(
            model=PlanningRequest, form_class=PlanningRequestForm
        ),
        name="planning_planningrequest_create",
    ),
    path(
        "requests/<int:pk>/update/",
        generic.UpdateView.as_view(
            model=PlanningRequest, form_class=PlanningRequestForm
        ),
        name="planning_planningrequest_update",
    ),
    path(
        "requests/<int:pk>/delete/",
        generic.DeleteView.as_view(model=PlanningRequest),
        name="planning_planningrequest_delete",
    ),
    # Planned work
    path(
        "work/",
        generic.ListView.as_view(
            model=PlannedWork, search_form_class=PlannedWorkSearchForm
        ),
        name="planning_plannedwork_list",
    ),
    path(
        "work/<int:pk>/",
        generic.DetailView.as_view(model=PlannedWork),
        name="planning_plannedwork_detail",
    ),
    path(
        "work/create/",
        generic.CreateView.as_view(model=PlannedWork, form_class=PlannedWorkForm),
        name="planning_plannedwork_create",
    ),
    path(
        "work/<int:pk>/update/",
        generic.UpdateView.as_view(model=PlannedWork, form_class=PlannedWorkForm),
        name="planning_plannedwork_update",
    ),
    path(
        "work/<int:pk>/delete/",
        generic.DeleteView.as_view(model=PlannedWork),
        name="planning_plannedwork_delete",
    ),
]