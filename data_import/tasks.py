from celery import shared_task
from django.conf import settings
import logging, dropbox, redis, json, re, csv
from .importers import ProductImporter

log = logging.getLogger('django')
dbx = dropbox.Dropbox(settings.DROPBOX_TOKEN)
redis_client = redis.StrictRedis(host=settings.REDIS_DOMAIN,
                                 db=settings.REDIS_DB,
                                 port=settings.REDIS_PORT)
export_folder = '/e-commerce'
redis_namespace = 'dropbox'
type_company_pattern = re.compile(r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$')

@shared_task
def handle_webhook(account):

    log.debug('calling handle_webhook()')

    # For data associated with this dropbox account
    account_key = '{}:{}'.format(redis_namespace, account)

    # cursor for the user (None the first time)
    cursor_key = '{}:cursors'.format(account_key)
    # DEBUG cursor = redis_client.hget(cursor_key, account)
    cursor = None
    # convert bytes from redis to string 
    try:
        cursor = cursor.decode('utf-8')
    except AttributeError:
        pass

    # fetch the results
    files = list()
    has_more = True
    while has_more:
        if cursor is None:
            result = dbx.files_list_folder(path='', recursive=True)
        else:
            result = dbx.files_list_folder_continue(cursor)

        for entry in result.entries:
            # toss entries not in the export folder and non-csv files
            if (not entry.path_lower.startswith(export_folder) or
                not entry.path_lower.endswith('.csv') or
                isinstance(entry, dropbox.files.DeletedMetadata) or
                isinstance(entry, dropbox.files.FolderMetadata)):
                continue

            # save the metadata
            files.append(entry)

        # Update cursor
        cursor = result.cursor
        redis_client.hset(cursor_key, account, cursor)

        # Repeat only if there's more to do
        has_more = result.has_more

    # get set of company names and export types
    export_company_set = set([_get_type_company_from_filename(f.name) for f in files])

    # get the most recent file for each company and type
    files.sort(key=lambda x: x.server_modified, reverse=True)
    for export_type, company in export_company_set:
        filtered = filter(lambda x: export_type in x.name and company in x.name, files)
        # now get and save the data for each file into the database
        latest_file = next(filtered)
        fetch_data.delay(export_type, company, latest_file.id)

@shared_task
def fetch_data(export_type, company, file_id):
    _, response = dbx.files_download(file_id)

    if export_type == 'Inventory':

        pass
    elif export_type == 'Product':
        importer = ProductImporter()
        importer.import_data(response.text)
        pass

    log.debug(file_csv)

def _get_type_company_from_filename(filename):
    match = type_company_pattern.match(filename)
    if match:
        return match.group(1,2)
    else:
        return None
