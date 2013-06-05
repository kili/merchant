from django.http import HttpResponse
from django.conf.urls import patterns
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from merchant.integrations.world_pay_integration import WorldPayIntegration as Integration
from merchant.contrib.django.billing.signals import transaction_was_successful, transaction_was_unsuccessful
from merchant.contrib.django.billing.models.world_pay_models import WorldPayResponse
from merchant.contrib.django.billing.forms.world_pay_forms import WPHostedPaymentForm

RBS_HOSTED_URL_TEST = "https://select-test.wp3.rbsworldpay.com/wcc/purchase"
RBS_HOSTED_URL_LIVE = "https://secure.wp3.rbsworldpay.com/wcc/purchase"

# http://www.rbsworldpay.com/support/bg/index.php?page=development&sub=integration&c=WW

csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)


class WorldPayIntegration(Integration):

    @property
    def service_url(self):
        if self.test_mode:
            return RBS_HOSTED_URL_TEST
        return RBS_HOSTED_URL_LIVE

    def form_class(self):
        return WPHostedPaymentForm

    def generate_form(self):
        return self.form_class()(initial=self.fields)

    @csrf_exempt_m
    @require_POST_m
    def notify_handler(self, request):
        post_data = request.POST.copy()
        data = {}

        resp_fields = {
            'instId': 'installation_id',
            'compName': 'company_name',
            'cartId': 'cart_id',
            'desc': 'description',
            'amount': 'amount',
            'currency': 'currency',
            'authMode': 'auth_mode',
            'testMode': 'test_mode',
            'transId': 'transaction_id',
            'transStatus': 'transaction_status',
            'transTime': 'transaction_time',
            'authAmount': 'auth_amount',
            'authCurrency': 'auth_currency',
            'authAmountString': 'auth_amount_string',
            'rawAuthMessage': 'raw_auth_message',
            'rawAuthCode': 'raw_auth_code',
            'name': 'name',
            'address': 'address',
            'postcode': 'post_code',
            'country': 'country_code',
            'countryString': 'country',
            'tel': 'phone',
            'fax': 'fax',
            'email': 'email',
            'futurePayId': 'future_pay_id',
            'cardType': 'card_type',
            'ipAddress': 'ip_address',
            }

        for (key, val) in resp_fields.iteritems():
            data[val] = post_data.get(key, '')

        try:
            resp = WorldPayResponse.objects.create(**data)
            # TODO: Make the type more generic
            transaction_was_successful.send(sender=self.__class__, type="purchase", response=resp)
            status = "SUCCESS"
        except:
            transaction_was_unsuccessful.send(sender=self.__class__, type="purchase", response=post_data)
            status = "FAILURE"

        return HttpResponse(status)

    def get_urls(self):
        urlpatterns = patterns('', (r'^rbs-notify-handler/$', self.notify_handler),)
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()