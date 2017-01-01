from django.db import models
from django.conf import settings
import re


import logging

log = logging.getLogger('django')

class Color(models.Model):
    # name from Momentis database
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=8)

    # name to display on the website
    _display_name = models.CharField(max_length=64)

    @property
    def display_name(self):
        if not self._display_name:
            return self.name
        else:
            return self._display_name

    def __str__(self):
        return '{} - {}'.format(self.name, self.code)

    def save(self, *args, **kwargs):
        # create the corrected color name
        self._display_name = correct_color_name(self.name.lower())
        super().save(*args, **kwargs)

class Size(models.Model):
    name = models.CharField(max_length=8)
    display_name = models.CharField(max_length=32)

    def __str__(self):
        return str(self.name)


class Product(models.Model):
    style_number = models.CharField(max_length=64, unique=True)
    season = models.CharField(max_length=128)
    name = models.CharField(max_length=256)
    department = models.CharField(max_length=64)
    division = models.CharField(max_length=64)
    available_start = models.DateField(blank=True, null=True)
    available_end = models.DateField(blank=True, null=True)
    description = models.TextField()
    archived = models.BooleanField()
    brand_id = models.CharField(max_length=64)
    wholesale_usd = models.DecimalField(max_digits=9, decimal_places=2)
    retail_usd = models.DecimalField(max_digits=9, decimal_places=2)
    wholesale_cad = models.DecimalField(max_digits=9, decimal_places=2)
    retail_cad = models.DecimalField(max_digits=9, decimal_places=2)

    # TODO: create a category hierarchy, using mptt or treebeard this could be
    # used to create the evening wear and bridal parent categories then have
    # their sub-categories.
    category = models.CharField(max_length=64)

    colors = models.ManyToManyField(Color)

    sizes = models.ManyToManyField(Size)

    def __str__(self):
        return '{} - {} - {}'.format(self.style_number, self.season, self.name)

    def in_stock(self):
        for variant in self.variant_set.all():
            if variant.inventory > 0:
                return True
        return False

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class VariantQueryset(models.query.QuerySet):
    def get_by_sku(self, sku):
        style_number, size_name, color_name = sku.split('-')
        variant = None
        try:
            # get and return the variant with the color name in plain uppercase
            color_name_1 = color_name.upper()
            log.debug('color1: {}'.format(color_name_1))
            variant = self.get(
                color__name=color_name_1,
                size__name=size_name,
                product__style_number=style_number,
            )
        except Exception as e:
            # try getting the variant with an uncorrected version of the color name
            log.warning(e)
            try:
                color_name_2 = uncorrect_color_name(color_name)
                log.debug('color2: {}'.format(color_name_2))
                variant = self.get(
                    color__name=color_name_2,
                    size__name=size_name,
                    product__style_number=style_number,
                )
            except Exception as e:
                log.warning(e)
                log.warning('missing color name: {}, for variant id: {}'.format(color_name_2, variant.id))

        return variant

class VariantManager(models.Manager):
    def get_queryset(self):
        return VariantQueryset(self.model, using=self._db)

    def get_by_sku(self, sku):
        return self.get_queryset().get_by_sku(sku)

class Variant(models.Model):
    upc = models.BigIntegerField(unique=True)
    product = models.ForeignKey(Product, on_delete = models.CASCADE)
    color = models.ForeignKey(Color, on_delete = models.CASCADE)
    size = models.ForeignKey(Size, on_delete = models.CASCADE)
    inventory = models.SmallIntegerField(default=0)

    objects = VariantManager()

    @property
    def sku(self):
        return '{}-{}-{}'.format(
            self.product.style_number,
            self.size.name,
            self.color.name)


color_abbreviations = {"blk/watermelon": "black/watermelon",
                       "blush/mid": "blush/midnight",
                       "prb  - prussian blue": "prussian blue",
                       "blk/midnight": "black/midnight",
                       "blk pewter": "black pewter",
                       "blk/teal": "black/teal",
                       "blk/gold": "black/gold",
                       "champ/silver": "champagne/silver",
                       "creme": "cream",
                       "blk": 'black'}

color_unfix_abbreviations = {v: k for k, v in color_abbreviations.items()}

# unfix color name abbreviations
def uncorrect_color_name(color):
    if color in color_unfix_abbreviations:
        uncorrected_color = color_unfix_abbreviations[color].upper()
        return uncorrected_color
    else:
        return color.upper()

# fix color name abbreviations
def correct_color_name(color):
    if color in color_abbreviations:
        corrected_color = color_abbreviations[color]
        return corrected_color
    else:
        return color

# TODO: Use this later to create a category hierarchy.
# class Category(models.Model):
#     category


class ImportFileMeta:
    type_company_regex = r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$'
    type_company_pattern = re.compile(type_company_regex)

    def __init__(self, filemeta):
        if not self.is_import_filemeta(filemeta):
            raise Exception(
                'Invalid FileMetaData passed to ImportFileMetaconstructor')
        self.filemeta = filemeta
        self.export_type, self.company = self._get_type_company_from_filename(
            filemeta.name)

    def _get_type_company_from_filename(self, filename):
        match = self.type_company_pattern.match(filename)
        if match:
            return match.group(1,2)
        else:
            return None

    @property
    def id(self):
        return self.filemeta.id

    @classmethod
    def is_import_filemeta(cls, filemeta):
        """
        Tests a FileMetaData instance to see if it is a valid Import file.
        """
        return (cls.type_company_pattern.match(filemeta.name) and
                filemeta.path_lower.startswith(
                    settings.DROPBOX_EXPORT_FOLDER))

class ImportFileMetaSet:
    # Export type keys
    PRODUCT = 'Product'
    INVENTORY = 'Inventory'

    def __init__(self, import_files):
        self.files = import_files
        self.company_set = set(
            f.company for f in self.files)
        self.export_type_set = set(
            f.export_type for f in self.files)

    def get_filtered_by_company_type(self, company, export_type):
        return [
            f for f in self.files
            if f.company == company and
            f.export_type == export_type
        ]

    def get_most_recent_file_from_list(self, file_list):
        if len(file_list):
            # sort by server modified time, newest first
            file_list.sort(key=lambda x: x.filemeta.server_modified,
                            reverse=True)
            return file_list[0]
        else:
            return None

    def get_prod_inv_ids_by_company(self, company):
        prod = self.get_most_recent_file_from_list(
            self.get_filtered_by_company_type(company, self.PRODUCT))

        inv = self.get_most_recent_file_from_list(
            self.get_filtered_by_company_type(company, self.INVENTORY))

        return (prod.id, inv.id)

    def get_import_file_ids(self):
        """get the import files by company"""

        if len(self.files):
            return {
                company: self.get_prod_inv_ids_by_company(company)
                for company in self.company_set
            }
        else:
            return False

    def get_import_files_by_company(self, company):
        prod = self.get_most_recent_file_from_list(
            self.get_filtered_by_company_type(company, self.PRODUCT))

        inv = self.get_most_recent_file_from_list(
            self.get_filtered_by_company_type(company, self.INVENTORY))

        return (prod, inv)

    def get_import_files(self):
        if len(self.files):
            return {
                company: self.get_import_files_by_company(company)
                for company in self.company_set
            }
        else:
            return False


class ImportFileQueryset(models.query.QuerySet):
    def get_by_company_export_type(self, company, export_type):
        return self.filter(company=company, export_type=export_type)

class ImportFileManager(models.Manager):
    def get_queryset(self):
        return ImportFileQueryset(self.model, using=self._db)

    def get_by_company_export_type(self, company, export_type):
        return self.get_queryset().get_by_company_export_type(company, export_type)

class ImportFile(models.Model):
    class Meta:
        get_latest_by = 'server_modified'

    # Export Types
    PRODUCT = 'Product'
    INVENTORY = 'Inventory'

    # Import Statuses
    IMPORTED = 'IMPORTED'
    IN_PROGRESS = 'IN_PROGRESS'
    NOT_IMPORTED = 'NOT_IMPORTED'

    IMPORT_STATUS_CHOICES = (
        (IMPORTED, 'Imported'),
        (IN_PROGRESS, 'In Progress'),
        (NOT_IMPORTED, 'Not Imported'),
    )

    type_company_pattern = re.compile(
        r'\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$')
    dropbox_id = models.CharField(unique=True, max_length=64)
    path_lower = models.CharField(max_length=1024)
    server_modified = models.DateTimeField()
    company = models.CharField(max_length=64)
    export_type = models.CharField(max_length=64)
    import_status = models.CharField(max_length=16,
                                     choices=IMPORT_STATUS_CHOICES,
                                     default=NOT_IMPORTED)

    objects = ImportFileManager()

    def save(self, *args, **kwargs):
        # get the company and export type from the filename during save
        self._parse_company_export_type()
        super().save(*args, **kwargs)

    def _parse_company_export_type(self):
        """Parse the company and export_type from filename."""
        match = self.type_company_pattern.match(self.path_lower)
        if match:
            self.company = match.group(2)
            self.export_type = match.group(1)
        else:
            raise ValueError(
                'Company or export type not found in filename: {}'
                .format(self.path_lower))
