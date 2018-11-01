import re, logging

from decimal import *
from datetime import datetime, timedelta


log = logging.getLogger('django')

NON_NUMERIC = re.compile(r'[^\d]+')
SIX_DIGITS = re.compile(r'^\d{6}$')

def parse_style_number(s):
    """Strip alpha chars and ensure style number is 6 digits long"""
    try:
        s = NON_NUMERIC.sub('', str(s))
    except:
        raise ValueError('Style number ({}) is invalid'.format(s))

    if SIX_DIGITS.match(s):
        return int(s)
    else:
        raise ValueError('Style number ({}) is not 6 digits long'.format(s))

def is_upc_valid(upc):
    # upc should be an int, or something that can cast to an int
    try:
        upc = int(upc)
    except:
        return False

    # upc should be 12 digits long
    return len(str(upc)) == 12

def valid_upc_or_none_from_str(upc):
    """return a valid upc from passed string or None"""
    if is_upc_valid(upc):
        return int(upc)
    else:
        return None

def date_or_none_from_string(date_string):
    date_format = '%m/%d/%Y'

    # skip over blank dates
    if date_string:
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError as e:
            log.warning(
                'ValueError while converting date_string: {} to datetime'
                .format(date_string))
            log.exception(e)

    # default to returning none
    return None

def make_decimal_or_none(value):
    try:
        return Decimal(str(value))
    except Exception as e:
        log.warning('Got exception converting "{}" to Decimal.'
                  .format(value))
        log.exception(e)
        return None

def bool_from_y_n(s):
    return s.lower() == 'y'

def int_or_default(x, default):
    try:
        return int(x)
    except:
        return default

def int_or_none(x):
    return int_or_default(x, None)

def int_or_zero(x):
    return int_or_default(x, 0)

def years_ago(n):
    """Return a datetime object for n years ago"""
    DAYS_PER_YEAR = 365
    return (datetime.now() - timedelta(days=n*DAYS_PER_YEAR))


# Color name conversion
def replace_spaces_with(string, replace):
    """Replace spaces in string with value of replace"""
    return re.sub(r'\s', replace, string)

def forward_slash_to_mixedCase(string):
    """Remove forward slash and change case of following letter to uppercase"""
    return re.sub(
        r'/([a-zA-Z]?)',
        lambda m: m.group(1).upper(), string)
