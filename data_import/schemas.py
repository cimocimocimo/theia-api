from .helpers import *

class Schema:
    """
    Encapsulates the logic for reading and writing each CSV format.
    describes how each of the columns in the rows of a CSV file map
    to Products and vice versa.
    """

    def __init__(self, *columns):
        self.columns = dict()

        for key, load_fn, save_fn in columns:
            self.columns[key] = Column(key, load_fn, save_fn)

class Column:
    def __init__(self, name, load_fn, save_fn):
        self.name = name

        if callable(load_fn):
            self.load = load_fn
        else:
            self.load = lambda x: x

        if callable(save_fn):
            self.save = save_fn
        else:
            self.save = lambda x: x

schemas = {
    'Inventory': Schema(
        ('UPC', valid_upc_from_str, valid_upc_from_str),
        ('QUANTITY', int_or_zero, int_or_zero),
        ('DATE', str, str),
    ),
    'Product': Schema(
        ('SEASON', str, str),
        ('STYLE NUMBER', parse_style_number, parse_style_number),
        ('NAME', str, str),
        ('COLOR', str, str), # TODO: use the color name correct fn here
        ('COLOR CODE', str, str),
        ('DEPARTMENT', str, str),
        ('DIVISION', str, str),
        ('ADDITIONAL SEASONS', str, str),
        ('WHOLESALE USD', make_decimal_or_none, make_decimal_or_none),
        ('RETAIL USD', make_decimal_or_none, make_decimal_or_none),
        ('CATEGORY', str, str),
        ('SUBCATEGORY', str, str),
        ('AVAILABLE START', date_or_none_from_string, date_or_none_from_string),
        ('AVAILABLE END', date_or_none_from_string, date_or_none_from_string),
        ('DESCRIPTION', str, str),
        ('ARCHIVED', bool_from_y_n, bool_from_y_n),
        ('BRAND ID', str, str),
        ('WHOLESALE CAD', make_decimal_or_none, make_decimal_or_none),
        ('RETAIL CAD', make_decimal_or_none, make_decimal_or_none),
        ('SIZE 1', int_or_none, int_or_none),
        ('UPC 1', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 2', int_or_none, int_or_none),
        ('UPC 2', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 3', int_or_none, int_or_none),
        ('UPC 3', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 4', int_or_none, int_or_none),
        ('UPC 4', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 5', int_or_none, int_or_none),
        ('UPC 5', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 6', int_or_none, int_or_none),
        ('UPC 6', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 7', int_or_none, int_or_none),
        ('UPC 7', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 8', int_or_none, int_or_none),
        ('UPC 8', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 9', int_or_none, int_or_none),
        ('UPC 9', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 10', int_or_none, int_or_none),
        ('UPC 10', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 11', int_or_none, int_or_none),
        ('UPC 11', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 12', int_or_none, int_or_none),
        ('UPC 12', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 13', int_or_none, int_or_none),
        ('UPC 13', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 14', int_or_none, int_or_none),
        ('UPC 14', valid_upc_from_str, valid_upc_from_str),
        ('SIZE 15', int_or_none, int_or_none),
        ('UPC 15', valid_upc_from_str, valid_upc_from_str),
    ),
}

