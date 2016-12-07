from django.db import models

class Color(models.Model):
    # name from Momentis database
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=8)
    # name to display on the website
    display_name = models.CharField(max_length=64)

    def __str__(self):
        return '{} - {}'.format(self.name, self.code)

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


class Variant(models.Model):
    upc = models.BigIntegerField(unique=True)
    product = models.ForeignKey(Product, on_delete = models.CASCADE)
    color = models.ForeignKey(Color, on_delete = models.CASCADE)
    size = models.ForeignKey(Size, on_delete = models.CASCADE)
    inventory = models.SmallIntegerField(default=0)

# TODO: Use this later to create a category hierarchy.
# class Category(models.Model):
#     category
