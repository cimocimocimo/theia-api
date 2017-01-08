from django.test import TestCase
from django.conf import settings
from django.utils import timezone
import os, logging
from datetime import timedelta

from .mixins import LoadTestDataMixin

from ..interfaces import DropboxInterface
from ..models import (Product, Variant, Color, ColorNameCorrection, Size,
                      ImportFile, Company, ExportType)
from ..importers import ProductImporter, InventoryImporter

log = logging.getLogger('django')

# TODO: Try using django-autofixure for running these tests
class TestProduct(LoadTestDataMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_in_stock(self):
        # variants_in_stock = Variant.objects.order_by('?').filter(inventory__gt=0)[0:10]
        # print(variants_in_stock)
        # for variant in variants_in_stock:
        #     variant.product.in_stock
        # self.assertTrue(.in_stock)
        pass

class TestVariant(TestCase):
    @classmethod
    def setUpClass(cls):
        ColorNameCorrection.objects.create(
            incorrect='blk',
            correct='black',
        )
        product = Product.objects.create(
            style_number=123456,
            archived=False,
            wholesale_usd=0,
            retail_usd=0,
            retail_cad=0,
            wholesale_cad=0,
        )
        color = Color.objects.create(
            momentis_name='RED',
            code='RED',
        )
        size = Size.objects.create(
            name='X',
        )
        variant = Variant.objects.create(
            upc=12341234123412,
            product=product,
            color=color,
            size=size,
        )

        product = Product.objects.create(
            style_number=123457,
            archived=False,
            wholesale_usd=0,
            retail_usd=0,
            retail_cad=0,
            wholesale_cad=0,
        )
        color = Color.objects.create(
            momentis_name='BLK',
            code='BLK',
        )
        variant = Variant.objects.create(
            upc=12341234123413,
            product=product,
            color=color,
            size=size,
        )

        super().setUpClass()


    def test_get_by_sku(self):
        for v in Variant.objects.all():
            print(v.sku)

        test_sku = '123456-X-red'
        print(test_sku)
        variant = Variant.objects.get(sku=test_sku)
        self.assertEqual(variant.upc, 12341234123412)

        test_sku = '123457-X-black'
        print(test_sku)
        variant = Variant.objects.get(sku=test_sku)
        self.assertEqual(variant.upc, 12341234123413)

class ImportFileTest(TestCase):
    def test_parse_company_export_type(self):
        filename = '00000000000000.SHPFY_ExportTypeExtract_CompanyName.CSV'
        company, export_type = ImportFile.parse_company_export_type(filename)
        self.assertEqual(company, 'CompanyName')
        self.assertEqual(export_type, 'ExportType')

    def test_get_latest(self):
        # add a few import files
        c = Company.objects.create(name='CompanyName')
        t = ExportType.objects.create(name='Product')
        ImportFile.objects.create(
            dropbox_id='1',
            path_lower='00000000000000.shpfy_productextract_companyname.csv',
            filename='00000000000000.SHPFY_ProductExtract_CompanyName.CSV',
            company=c, export_type=t,
            server_modified=timezone.now(),
        )
        ImportFile.objects.create(
            dropbox_id='2',
            path_lower='00000000000000.shpfy_productextract_companyname.csv',
            filename='00000000000000.SHPFY_ProductExtract_CompanyName.CSV',
            company=c, export_type=t,
            server_modified=timezone.now()-timedelta(1),
        )
        t = ExportType.objects.create(name='Inventory')
        ImportFile.objects.create(
            dropbox_id='3',
            path_lower='00000000000000.shpfy_inventoryextract_companyname.csv',
            filename='00000000000000.SHPFY_InventoryExtract_CompanyName.CSV',
            company=c, export_type=t,
            server_modified=timezone.now(),
        )
        ImportFile.objects.create(
            dropbox_id='4',
            path_lower='00000000000000.shpfy_inventoryextract_companyname.csv',
            filename='00000000000000.SHPFY_InventoryExtract_CompanyName.CSV',
            company=c, export_type=t,
            server_modified=timezone.now()-timedelta(3),
        )
        latest_product = c.importfile_set.filter(export_type__name='Product').latest()
        latest_inventory = c.importfile_set.filter(export_type__name='Inventory').latest()
        self.assertEqual(latest_product.dropbox_id, '1')
        self.assertEqual(latest_inventory.dropbox_id, '3')

    def test_save(self):
        # after saving a proper import file from dropbox we should cache the
        # content file in redis

        # get the file listing of the entire dropbox
        dropbox = DropboxInterface()
        entries = dropbox.list_files(settings.DROPBOX_EXPORT_FOLDER)

        for e in entries['added']:
            # TODO: Remove this after we clean out the .osiris files
            if e.name.endswith('.osiris'):
                continue

            try:
                company_name, export_type_name = ImportFile.parse_company_export_type(e.name)
            except ValueError as e:
                log.warning(e)
                continue

            try:
                company, created = Company.objects.get_or_create(
                    name=company_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

            try:
                export_type, created = ExportType.objects.get_or_create(
                    name=export_type_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

            try:
                import_file, created = ImportFile.objects.update_or_create(
                    dropbox_id=e.id,
                    defaults={
                        'path_lower': e.path_lower,
                        'filename': e.name,
                        'server_modified': e.server_modified,
                        'company': company,
                        'export_type': export_type,
                    }
                )
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

class ColorTest(TestCase):
    # (incorrect, correct)
    color_correction_data = [
        ('blk/watermelon', 'black/watermelon'),
        ('blush/mid', 'blush/midnight'),
        ('prb  - prussian blue', 'prussian blue'),
        ('blk/midnight', 'black/midnight'),
        ('blk pewter', 'black pewter'),
        ('blk/teal', 'black/teal'),
        ('blk/gold', 'black/gold'),
        ('champ/silver', 'champagne/silver'),
        ('creme', 'cream'),
        ('blk' 'black'),
    ]

    def test_correct_color_name(self):
        # ensure that incorrect color names passed to Color constructors are
        # corrected on save.

        # create the color correction objects
        for i, correction in enumerate(self.color_correction_data):
            ColorNameCorrection.objects.create(
                incorrect=correction[0],
                correct=correction[1])

            color = Color.objects.create(
                momentis_name=correction[0],
                code=str(i)
            )
    
            # ensure the names were corrected
            self.assertEqual(color.name, correction[1])
