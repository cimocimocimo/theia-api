from enum import Enum
from .models import Color, Size, Product, Variant
import csv
from datetime import datetime

"""
These import the Product and Inventory CSV files
This should take the text of the body of the csv file downloaded
clean it up, remove the extra comma
then process all the lines of that file to create the needed objects
"""

class ImporterBase:
    def __init__(self, text):
        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.rstrip(',') for l in lines]
        self.csv = csv.DictReader(lines)

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

class ProductImporter(ImporterBase):
    date_format = '%m/%d/%Y'

    def __init__(self, text):
        super().__init__(text)

    def import_data(self):
        for row in self.csv:
            prod, prod_created = Product.objects.get_or_create(
                season=row[ProdHeaders.season],
                style_number=row[ProdHeaders.style],
                name=row[ProdHeaders.name],
                department=row[ProdHeaders.department],
                division=row[ProdHeaders.division],
                available_start=self._date_or_none_from_string(row[ProdHeaders.avail_start]),
                available_end=self._date_or_none_from_string(row[ProdHeaders.avail_end]),
                description=row[ProdHeaders.description],
                archived=(True if row[ProdHeaders.archived] == 'Y' else False),
                brand_id=row[ProdHeaders.brand_id],
                wholesale_usd=row[ProdHeaders.wholesale_usd],
                retail_usd=row[ProdHeaders.retail_usd],
                wholesale_cad=row[ProdHeaders.wholesale_cad],
                retail_cad=row[ProdHeaders.retail_cad],
                category=row[ProdHeaders.category],
            )
            color, color_created = Color.objects.get_or_create(
                name=row[ProdHeaders.color],
                code=row[ProdHeaders.color_code],
            )
            # add color to product
            prod.colors.add(color)
            for x in size_upc_range:
                size_value = row[size_header_format.format(x)]
                upc_value = row[upc_header_format.format(x)]
                # skip if size is blank
                if not size_value:
                    continue

                # if product was just created need to add sizes to it
                if prod_created:
                    size, size_created = Size.objects.get_or_create(
                        name=size_value
                    )
                    prod.sizes.add(size)

                # create variants for this combo of size and colors
                Variant.objects.create(
                    upc=upc_value,
                    product=prod,
                    color=color,
                    size=size,
                )

    def _date_or_none_from_string(self, date_string):
        try:
            return datetime.strptime(date_string, self.date_format)
        except ValueError:
            return None

class InventoryImporter(ImporterBase):
    def __init__(self):
        super().__init__(text)

