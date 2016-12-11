"""
The data exporter.

This takes the data in the DB and exports it to other formats and apis. It
encapsulates the logic needed to translate the local models into the formats
needed for the various destinations.
"""

class ExporterBase:
    pass

class ShopifyExporter(ExporterBase):
    pass


