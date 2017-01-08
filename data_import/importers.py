from .models import Color, Size, Product, Variant
from .helpers import *
import csv, logging

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
    def import_data(self, import_file):
        for row in import_file.rows():
            self.process_row(row)

    def _text_to_csv(self, text):
        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.rstrip(',') for l in lines]
        return csv.DictReader(lines)

    def process_row(self, row):
        pass

class ProductImporter(ImporterBase):
    styles_imported = set()

    def process_row(self, row):
        if not row:
            return

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
                'name': row[ProdHeaders.color],
            }
        )

        # add color to product
        prod.colors.add(color)
        for x in size_upc_range:
            size_value = row[size_header_format.format(x)]
            upc_value = row[upc_header_format.format(x)]

            # skip if size or upc is blank
            if not size_value or not is_upc_valid(upc_value):
                continue

            # create size object if needed
            size, size_created = Size.objects.get_or_create(
                name=size_value
            )

            # if product was just created need to add sizes to it
            if prod_created:
                prod.sizes.add(size)

            # create variants for this combo of size and colors
            Variant.objects.update_or_create(
                upc=upc_value,
                defaults={
                    'product': prod,
                    'color': color,
                    'size': size,
                }
            )

        # keep set of style numbers
        self.styles_imported.add(style_number)

class InventoryImporter(ImporterBase):
    missing_upcs = 0

    """
    Import the inventory to redis

    set of the UPCS

    hash of each data line keyed by UPC

    python redis methods to use
    .hget(name, key) - returns value for hash key
    .hgetall(name) - returns dict
    .hset(name, key, value) - individually set keys/values for hash
    .hmset(name, mapping [dict]) - sets multiple values for hash with name
    .expire(name, seconds) - seconds can be an integer or timedelta obj.

    .sadd(name, value) - add value to set

    """

    def __init__(self):
        super().__init__()

    def process_row(self, row):
        data_error = False

        upc = row['UPC']
        quantity = row['QUANTITY']
        date = row['DATE']

        try:
            variant = Variant.objects.get(upc=upc)
        except Variant.DoesNotExist:
            log.error('Inventory UPC: {} does not exist'.format(upc))
            self.missing_upcs += 1
        else:
            if variant.inventory != quantity:
                variant.inventory = quantity
                variant.save(update_fields=['inventory'])

