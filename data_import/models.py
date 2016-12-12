from django.db import models

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
        print(self.name)
        print(self._display_name)
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
        return ''

    def in_stock(self):
        for variant in self.variant_set.all():
            if variant.inventory > 0:
                return True
        return False

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

# TODO: Use this later to create a category hierarchy.
# class Category(models.Model):
#     category
