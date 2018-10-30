import csv, logging

from core.controllers import Collector
from .schemas import schemas

log = logging.getLogger('development')


class CSVRows:
    """Provides an itererator interface for the ImportFile csv data"""

    def __init__(self, text, schema_name):
        self.schema = self.schemas[schema_name]

        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.decode('utf8').rstrip(',') for l in lines]
        self.numb_lines_total = len(lines)
        self._csv_reader = csv.DictReader(lines)
        # map each column's schema for each column that is in the data
        self.columns = dict()
        for h in self._csv_reader.fieldnames:
            try:
                self.columns[h] = self.schema.columns[h]
            except KeyError:
                pass

    def __iter__(self):
        return self

    # TODO: Gather the specific errors here and the row and column info for
    # errors. Log these to the import job somehow.
    # I think I need to add an is_valid function to the schema so that I can
    # test the values before I load them. The load function does it's best
    # to return a usable value.
    # Also if load is not able to return a usable value, like with invalid
    # UPCs, we should skip that line, record the line number, and try to
    # process the next line.
    def __next__(self):
        raw_dict = next(self._csv_reader)
        processed = dict()
        for k,v in raw_dict.items():
            try:
                processed[k] = self.columns[k].load(v)
            except IndexError:
                pass
            except ValueError as e:
                log.exception(e)
                log.warning('Row contains invalid data')
                log.warning(raw_dict)
                return None
        return processed
