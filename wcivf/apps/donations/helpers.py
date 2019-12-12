from django.conf import settings
from django.utils.crypto import get_random_string

import gocardless_pro
import stripe
from stripe.error import StripeError

PAYMENT_TYPES = (
    ("subscription", "Monthly donation"),
    ("bill", "Single donation"),
)

PAYMENT_UNITS = ((3, "£3"), (10, "£10"), (25, "£25"), (50, "£50"))


class GoCardlessHelper(object):
    def __init__(self, request):
        self.request = request
        # We need the session to be saved before it gets a session_key
        # This is because the code is called from a middleware
        self.request.session.save()

        if not self.request.session.get("GC_SESSION_KEY"):
            self.request.session["GC_SESSION_KEY"] = get_random_string(
                length=50
            )

        if getattr(settings, "GOCARDLESS_USE_SANDBOX", False):
            gc_environment = "sandbox"
        else:
            gc_environment = "live"

        self.client = gocardless_pro.Client(
            access_token=settings.GOCARDLESS_ACCESS_TOKEN,
            environment=gc_environment,
        )

    def get_redirect_url(self):
        """
        Get a URL for creating a customer object.
        """
        redirect_flow = self.client.redirect_flows.create(
            params={
                "description": settings.GO_CARDLESS_PAYMENT_DESCRIPTION,
                "session_token": self.request.session["GC_SESSION_KEY"],
                "success_redirect_url": settings.GOCARDLESS_REDIRECT_URL,
            }
        )

        # Save the flow ID on the session
        self.request.session["GC_REDIRECT_FLOW_ID"] = redirect_flow.id
        self.request.session.save()
        return redirect_flow.redirect_url

    def confirm_redirect_flow(self):
        redirect_flow = self.client.redirect_flows.complete(
            self.request.GET.get("redirect_flow_id"),
            params={"session_token": self.request.session["GC_SESSION_KEY"]},
        )
        self.request.session["GC_CUSTOMER_ID"] = redirect_flow.links.customer
        self.request.session["GC_MANDATE_ID"] = redirect_flow.links.mandate
        self.request.session.save()

    def create_payment(self):
        form = self.request.session["donation_form"]
        payment_type = form["payment_type"]
        assert payment_type in [i[0] for i in PAYMENT_TYPES]
        amount = form["amount"]
        if form["other_amount"]:
            amount = form["other_amount"]
        amount = int(float(amount) * 100)

        params = {
            "amount": amount,
            "currency": "GBP",
            "links": {"mandate": self.request.session["GC_MANDATE_ID"]},
        }
        if payment_type == "bill":
            # One off donation
            return self.client.payments.create(params)

        if payment_type == "subscription":
            # Monthly donation
            params["interval_unit"] = "monthly"
            params["day_of_month"] = "1"
            return self.client.subscriptions.create(params)


class StripeHelper:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = settings.STRIPE_API_KEY
        self.StripeException = StripeError

    def charge(
        self,
        amount,
        token,
        currency="gbp",
        description="Democracy Club Donation",
    ):
        stripe.Charge.create(
            amount=amount,
            currency=currency,
            description=description,
            source=token,
            metadata={"app": "wcivf"},
        )
