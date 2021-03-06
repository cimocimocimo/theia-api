import csv, logging, re
from datetime import timedelta
from django.db.utils import IntegrityError

from .interfaces import RedisInterface
from .models import Color, Size, Product, Variant, Inventory, ImportFile
from .helpers import *

log = logging.getLogger('django')

"""
These import the Product and Inventory CSV files
This should take the text of the body of the csv file downloaded
clean it up, remove the extra comma
then process all the lines of that file to create the needed objects
"""

class ProdHeaders():
    season = 'SEASON'
    style = 'STYLE NUMBER'
    name = 'NAME'
    color = 'COLOR'
    color_code = 'COLOR CODE'
    department = 'DEPARTMENT'
    division = 'DIVISION'
    addtl_seasons = 'ADDITIONAL SEASONS'
    wholesale_usd = 'WHOLESALE USD'
    retail_usd = 'RETAIL USD'
    category = 'CATEGORY'
    subcategory = 'SUBCATEGORY'
    avail_start = 'AVAILABLE START'
    avail_end = 'AVAILABLE END'
    description = 'DESCRIPTION'
    archived = 'ARCHIVED'
    brand_id = 'BRAND ID'
    wholesale_cad = 'WHOLESALE CAD'
    retail_cad = 'RETAIL CAD'

size_upc_range = range(1, 16)
size_header_format = 'SIZE {}'
upc_header_format = 'UPC {}'

class ImporterBase:
    def __init__(self):
        self.redis = RedisInterface()

    def pre_import_data(self):
        self.import_file.import_status = ImportFile.IN_PROGRESS
        self.import_file.save()
        pass

    def import_data(self, import_file):
        self.import_file = import_file

        self.pre_import_data()

        for row in import_file.rows():
            self.process_row(row)

        self.post_import_data()

    def post_import_data(self):
        self.import_file.import_status = ImportFile.IMPORTED
        self.import_file.save()
        pass

    def process_row(self, row):
        pass

class ProductImporter(ImporterBase):
    styles_imported = set()
    YEAR = re.compile(r'\d{4}')

    def get_year_from_season(self, season):
        # get the year from the season
        m = self.YEAR.search(season)
        if m:
            return int(m.group())
        else:
            return False

    # TODO: split this function into two parts
    # the first should create clean and process the row data and save it to redis
    # the second should then scan the data and either bulk create new db records, or
    # bulk update the items. This way I can split the importer into to jobs that
    # can be run in separate celery tasks.
    def process_row(self, row):
        if not row:
            return

        # skip dresses made before 3 years ago
        season_year = self.get_year_from_season(row[ProdHeaders.season])
        if season_year and season_year < years_ago(1).year:
            print('less than a year ago')
            return

        print('importing')

        log.debug('ProductImporter().process_row(row={})'
                  .format(row))

        style_number = row[ProdHeaders.style]

        # If this product was in the DB already but it's the first time we've
        # seen it in this import. Then let's update the product with the data
        # from this line in the spreadsheet.
        if style_number in self.styles_imported:
            # this has been imported already in a previous row
            # so we just need to get the product and the color and Variants to it.
            prod = Product.objects.get(style_number=style_number)
            prod_created = False
        else:
            # this has not been imported yet
            # get or update product for this row.
            # this is because the product may be in the db already. so we
            # update it if the data in the spreadsheet has changed
            prod, prod_created = Product.objects.update_or_create(
                style_number=style_number,
                defaults={
                    'season': row[ProdHeaders.addtl_seasons],
                    'name': row[ProdHeaders.name],
                    'department': row[ProdHeaders.department],
                    'division': row[ProdHeaders.division],
                    'available_start': row[ProdHeaders.avail_start],
                    'available_end': row[ProdHeaders.avail_end],
                    'description': row[ProdHeaders.description],
                    'archived': row[ProdHeaders.archived],
                    'brand_id': row[ProdHeaders.brand_id],
                    'wholesale_usd': row[ProdHeaders.wholesale_usd],
                    'retail_usd': row[ProdHeaders.retail_usd],
                    'wholesale_cad': row[ProdHeaders.wholesale_cad],
                    'retail_cad': row[ProdHeaders.retail_cad],
                    'category': row[ProdHeaders.category],
                }
            )

        # get or create the color option for this row
        color, color_created = Color.objects.update_or_create(
            code=row[ProdHeaders.color_code],
            defaults={
                'momentis_name': row[ProdHeaders.color],
            }
        )

        # add color to product
        prod.colors.add(color)
        for x in size_upc_range:
            size_value = row[size_header_format.format(x)]
            upc_value = row[upc_header_format.format(x)]

            # skip if size or upc is blank
            if size_value == None or not is_upc_valid(upc_value):
                continue

            # create size object if needed
            size, size_created = Size.objects.get_or_create(
                name=size_value
            )

            # if product was just created need to add sizes to it
            if prod_created:
                prod.sizes.add(size)

            # create variants for this combo of size and colors
            try:
                Variant.objects.update_or_create(
                    upc=upc_value,
                    defaults={
                        'product': prod,
                        'color': color,
                        'size': size,
                    }
                )
            except IntegrityError as e:
                log.exception(e)
                log.warning(
                    'Variant could not be created style: {}, upc: {}'.format(
                        prod.style_number, upc_value))

        # keep set of style numbers
        self.styles_imported.add(style_number)

        def post_import_data(self):
            # TODO: Remove this expire code once upcs are added on import.
            # set expire on variant key
            self.redis.client.expire('variant:sku_upc_map', timedelta(days=1))
            super().post_import_data()

class InventoryImporter(ImporterBase):
    """
    Import the inventory to redis

    set of the UPCS

    hash of each data line keyed by UPC
    """

    missing_upcs = 0

    def __init__(self):
        super().__init__()

    def pre_import_data(self):
        self.inventory = Inventory(self.import_file.company.name)
        self.inventory.reset()
        super().pre_import_data()

    def import_data(self, *args, **kwargs):
        super().import_data(*args, **kwargs)

    def post_import_data(self):
        super().post_import_data()

    def process_row(self, row):
        upc = row['UPC']

        # store upc in redis set
        self.inventory.add_item(upc, row)
