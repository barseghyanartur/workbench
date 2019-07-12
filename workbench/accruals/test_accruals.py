from datetime import date
from decimal import Decimal

from django.test import TestCase

from workbench import factories
from workbench.accruals.models import Accrual, CutoffDate
from workbench.reporting import key_data
from workbench.tools.forms import WarningsForm
from workbench.tools.testing import messages


class AccrualsTest(TestCase):
    def test_cutoff_days(self):
        self.client.force_login(factories.UserFactory.create())
        response = self.client.post("/accruals/create/", {"day": ""})
        self.assertContains(response, "Dieses Feld ist zwingend erforderlich.")
        response = self.client.post("/accruals/create/", {"day": "31.01.2019"})
        day = CutoffDate.objects.get()
        self.assertRedirects(response, day.urls["detail"])
        response = self.client.post(day.urls["delete"])
        self.assertRedirects(response, day.urls["list"])
        self.assertEqual(
            messages(response), ["Stichtag '31.01.2019' wurde erfolgreich gelöscht."]
        )

    def test_cutoff_day_warning(self):
        self.client.force_login(factories.UserFactory.create())
        response = self.client.post("/accruals/create/", {"day": "01.01.2019"})
        self.assertContains(
            response, "Ungewöhnlicher Stichtag (nicht letzter Tag des Monats)."
        )

        response = self.client.post(
            "/accruals/create/",
            {"day": "01.01.2019", WarningsForm.ignore_warnings_id: "unusual-cutoff"},
        )
        self.assertEqual(response.status_code, 302)

    def test_cutoff_days_with_accruals(self):
        project = factories.ProjectFactory.create()

        factories.InvoiceFactory.create(
            project=project,
            type=factories.Invoice.FIXED,
            invoiced_on=date(2018, 12, 1),
            status=factories.Invoice.SENT,
            subtotal=100,
        )
        down_payment = factories.InvoiceFactory.create(
            project=project,
            type=factories.Invoice.DOWN_PAYMENT,
            invoiced_on=date(2018, 12, 2),
            status=factories.Invoice.SENT,
            subtotal=100,
        )

        service = factories.ServiceFactory.create(
            project=project, effort_type="Programmierung", effort_rate=150
        )
        factories.LoggedHoursFactory.create(
            service=service, hours=1, rendered_on=date(2018, 12, 15)
        )

        self.client.force_login(factories.UserFactory.create())
        response = self.client.post("/accruals/create/", {"day": "31.12.2018"})
        day = CutoffDate.objects.get()
        self.assertRedirects(response, day.urls["detail"])

        response = self.client.get(day.urls["update"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(messages(response), [])

        response = self.client.get(day.urls["detail"] + "?create_accruals=1")
        self.assertRedirects(response, day.urls["detail"])
        self.assertEqual(messages(response), ["Abgrenzungen erstellt."])

        self.assertEqual(Accrual.objects.count(), 1)

        response = self.client.post(day.urls["delete"])
        self.assertRedirects(response, day.urls["detail"])
        self.assertEqual(
            messages(response),
            ["Kann Stichtag mit schon existierenden Abgrenzungen nicht bearbeiten."],
        )

        response = self.client.get(day.urls["update"])
        self.assertRedirects(response, day.urls["detail"])
        self.assertEqual(
            messages(response),
            ["Kann Stichtag mit schon existierenden Abgrenzungen nicht bearbeiten."],
        )

        response = self.client.get(day.urls["detail"] + "?xlsx=1")
        self.assertEqual(response.status_code, 200)

        accrual = Accrual.objects.get()
        self.assertEqual(accrual.cutoff_date, date(2018, 12, 31))
        self.assertEqual(accrual.work_progress, 50)  # 100 of fixed, 50 of down payment
        response = self.client.post(
            day.urls["detail"], {"id": accrual.id, "work_progress": 60}
        )
        self.assertEqual(response.status_code, 202)
        accrual.refresh_from_db()
        self.assertEqual(accrual.work_progress, 60)

        Accrual.objects.create(
            invoice=down_payment,
            cutoff_date=date(2019, 1, 31),
            work_progress=80,
            logbook=0,
        )

        # print(key_data.accruals_by_date())
        accruals = key_data.accruals_by_date()
        self.assertEqual(len(accruals), 2)

        self.assertEqual(accruals[(2018, 12)]["accrual"], Decimal(40))
        self.assertEqual(accruals[(2018, 12)]["delta"], Decimal(40))

        self.assertEqual(accruals[(2019, 1)]["accrual"], Decimal(20))
        self.assertEqual(accruals[(2019, 1)]["delta"], Decimal(-20))

        invoiced = key_data.invoiced_corrected([date(2018, 1, 1), date(2019, 2, 28)])
        self.assertEqual(len(invoiced), 1)
        self.assertEqual(len(invoiced[2018]), 1)
        self.assertEqual(invoiced[2018][12], Decimal(160))

    def test_future_cutoff_dates(self):
        self.client.force_login(factories.UserFactory.create())
        response = self.client.post("/accruals/create/", {"day": "31.01.2099"})
        day = CutoffDate.objects.get()
        self.assertRedirects(response, day.urls["detail"])

        response = self.client.get(day.urls["detail"] + "?create_accruals=1")
        self.assertRedirects(response, day.urls["detail"])
        self.assertEqual(
            messages(response),
            ["Kann Abgrenzungen für zukünftige Stichtage nicht generieren."],
        )

    def test_list(self):
        self.client.force_login(factories.UserFactory.create())
        self.assertEqual(self.client.get("/accruals/").status_code, 200)
        self.assertEqual(self.client.get("/accruals/?q=foo").status_code, 200)
