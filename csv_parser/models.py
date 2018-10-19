import csv, logging

log = logging.getLogger('development')

class CSVRows:
    """Provides an itererator interface for the ImportFile csv data"""

    from .schemas import schemas

    def __init__(self, text, schema_name):
        self.schema = self.schemas[schema_name]

        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.decode('utf8').rstrip(',') for l in lines]
        self._csv_reader = csv.DictReader(lines)

        self.columns = dict()
        # map each column's schema for each column that is in the data
        for h in self._csv_reader.fieldnames:
            try:
                self.columns[h] = self.schema.columns[h]
            except KeyError:
                pass

    def __iter__(self):
        return self

    # TODO: Gather the specific errors here and the row and column info for
    # errors. Log these to the import job somehow.
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
