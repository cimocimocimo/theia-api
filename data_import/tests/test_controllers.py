from django.test import TestCase
from django.conf import settings
import logging

from ..controllers import Controller
from ..models import Company

log = logging.getLogger('django')

class TestController(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_get_companies_or_none(self):
        # create some test companies
        test_company_data = [
            ('CompanyOne', 'shop_name_1', 'api_key_1', 'password_1'),
            ('CompanyTwo', 'shop_name_2', 'api_key_2', 'password_2'),
            ('CompanyThree', 'shop_name_3', 'api_key_3', 'password_3'),
        ]
        for data in test_company_data:
            Company.objects.create(name=data[0],
                                   shopify_shop_name=data[1],
                                   shopify_api_key=data[2],
                                   shopify_password=data[3])

        c = Controller()
        # get all if passed None
        companies = c._get_companies_or_none(None)
        self.assertEqual(3, len(companies))
        # passing a company name as a string should return that company
        companies = c._get_companies_or_none('CompanyOne')
        self.assertEqual('CompanyOne', companies[0].name)
        # and it should raise an exception if the passed company name does not
        # exist
        with self.assertRaises(Exception):
            c._get_companies_or_none('NotACompanyName')
