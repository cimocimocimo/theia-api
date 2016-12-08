from .models import Color, Size, Product, Variant
import csv
from datetime import datetime

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
    def import_data(self, text):
        self.text = text
        self.csv = self._text_to_csv(text)
        for row in self.csv:
            self.process_row(row)

    def _text_to_csv(self, text):
        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.rstrip(',') for l in lines]
        return csv.DictReader(lines)

    def _is_valid_upc(self, upc):
        try:
            upc = int(upc)
        except ValueError:
            return False

        if len(str(upc)) == 12:
            return True
        else:
            return False


    def process_row(self, row):
        pass

class ProductImporter(ImporterBase):
    date_format = '%m/%d/%Y'

    styles_imported = set()

    def process_row(self, row):
        # import data

        # style number
        style_number = row[ProdHeaders.style]
        season = row[ProdHeaders.season]
        name = row[ProdHeaders.name]
        department = row[ProdHeaders.department]
        division = row[ProdHeaders.division]
        available_start = self._date_or_none_from_string(row[ProdHeaders.avail_start])
        available_end = self._date_or_none_from_string(row[ProdHeaders.avail_end])
        description = row[ProdHeaders.description]
        archived = (True if row[ProdHeaders.archived] == 'Y' else False)
        brand_id = row[ProdHeaders.brand_id]
        wholesale_usd = row[ProdHeaders.wholesale_usd]
        retail_usd = row[ProdHeaders.retail_usd]
        wholesale_cad = row[ProdHeaders.wholesale_cad]
        retail_cad = row[ProdHeaders.retail_cad]
        category = row[ProdHeaders.category]

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
                    'season': season,
                    'name': name,
                    'department': department,
                    'division': division,
                    'available_start': available_start,
                    'available_end': available_end,
                    'description': description,
                    'archived': archived,
                    'brand_id': brand_id,
                    'wholesale_usd': wholesale_usd,
                    'retail_usd': retail_usd,
                    'wholesale_cad': wholesale_cad,
                    'retail_cad': retail_cad,
                    'category': category,
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

            # skip if size is blank
            if not size_value:
                continue

            # make sure the upc is valid
            if not self._is_valid_upc(upc_value):
                print('invalid upc value: {}'.format(upc_value))
                continue

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

    def _date_or_none_from_string(self, date_string):
        try:
            return datetime.strptime(date_string, self.date_format)
        except ValueError:
            return None

class InventoryImporter(ImporterBase):
    missing_upcs = 0

    def __init__(self):
        super().__init__()

    def process_row(self, row):
        data_error = False

        # get data from row
        upc_raw = row['UPC']
        try:
            upc = int(upc_raw)
        except ValueError:
            data_error = True
            print('invalid upc: {}'.format(upc_raw))

        inventory_raw = int(row['QUANTITY'])
        try:
            inventory = int(inventory_raw)
        except ValueError:
            data_error = True
            print('invalid inventory: {}'.format(upc_raw))

        # log or record errors
        if data_error:
            print('error in data: {}'.format(row))
            return

        try:
            variant = Variant.objects.get(upc=upc)
        except Variant.DoesNotExist:
            self.missing_upcs += 1
        else:
            if variant.inventory != inventory:
                variant.inventory = inventory
                variant.save(update_fields=['inventory'])

