import csv, logging

log = logging.getLogger('django')

class CSVRows:
    """Provides an itererator interface for the ImportFile csv data"""

    from .schemas import schemas

    def __init__(self, text, schema_name):
        self.text = text
        self.schema = self.schemas[schema_name]
        self.columns = dict()
        self._csv_reader = self._text_to_csv(self.text)
        self._map_columns(self._csv_reader.fieldnames)

    def _map_columns(self, headers):
        # map each column's schema for each column that is in the data
        for h in headers:
            try:
                self.columns[h] = self.schema.columns[h]
            except KeyError:
                pass

    def _text_to_csv(self, text):
        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.decode('utf8').rstrip(',') for l in lines]
        return csv.DictReader(lines)

    def __iter__(self):
        return self

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
