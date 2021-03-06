import logging, re, os, dropbox, redis
from datetime import timedelta
from pprint import pprint, pformat

from django.conf import settings


log = logging.getLogger('development')


class DropboxInterface:

    redis_namespace = 'dropbox'
    cursor_key_format = '{prefix}:cursor'

    def __init__(self):
        self.dropbox_client = dropbox.Dropbox(settings.DROPBOX_TOKEN)
        self.redis_client = redis.StrictRedis(host=settings.REDIS_DOMAIN,
                                                   db=settings.REDIS_DB,
                                                   port=settings.REDIS_PORT)
        self.__cursor = None

    # Upload, Delete, and Get Files
    def upload_files(self, files, path='/'):
        for f in files:
            self.dropbox_client.files_upload(
                f.read(),
                os.path.join(path, os.path.basename(f.name)))

    def delete_file(self, path):
        self.dropbox_client.files_delete(path)

    def download_file(self, id):
        return self.dropbox_client.files_download(id)

    def get_file_contents(self, id):
        filemeta, response = self.download_file(id)
        return response.text

    def list_all_files(self):
        # list all files in dropbox
        entries, cursor = self._get_result_entries(
            path=settings.DROPBOX_EXPORT_FOLDER, recursive=True)
        self._save_cursor(cursor)
        return entries

    def list_changed_files(self):
        """Lists the latest file changes in Dropbox.

        Should only be called when responding to a Dropbox webhook request. It
        expects that ImportFile instances have all been created for the files
        that were in Dropbox before the change. Also expects a file_list
        cursor to be stored in Redis.

        Raises RuntimeError if the initialization function hasn't been run.
        """

        cursor = self._get_cursor()
        if not cursor:
            raise RuntimeError

        entries, cursor = self._get_result_entries(
            cursor, path=settings.DROPBOX_EXPORT_FOLDER, recursive=True)
        self._save_cursor(cursor)
        return entries

    # Private Methods #########################################################

    def _format_cursor_key(self):
        return self.cursor_key_format.format(
            prefix=self.redis_namespace)

    def _save_cursor(self, cursor):
        key = self._format_cursor_key()
        expire = timedelta(days=7)
        self.redis_client.set(
            key,
            cursor)
        self.redis_client.expire(key, expire)

    def _get_cursor(self):
        # get the cursor, returns None if not present
        cursor = self.redis_client.get(
            self._format_cursor_key())
    
        # convert bytes from redis to string 
        try:
            return cursor.decode('utf-8')
        except AttributeError:
            return None

    def _delete_cursor(self):
        self.redis_client.delete(self._format_cursor_key())

    def _get_result_entries(self, cursor=None, *args, **kwargs):
        log.debug('calling _get_result_entries(cursor={}, args={}, kwargs={})'
                  .format(cursor, args, kwargs))

        entries = []
        has_more = True
        while has_more:

            # try the cursor continue
            if cursor is not None:
                try:
                    result = self.dropbox_client.files_list_folder_continue(cursor)
                except ApiError:
                    # invalid cursor so we set to None and get the full folder list
                    cursor = None

            if cursor is None:
                result = self.dropbox_client.files_list_folder(*args, **kwargs)

            entries.extend(result.entries)

            cursor = result.cursor
            has_more = result.has_more

        return entries, cursor

    # Need to initialize the worker state for dropbox
    # Get the files already present in dropbox.
    # then we only respond to file changes in dropbox
    def startup(self):
        # check for a dropbox cursor in redis

        # if we have a cursor then we've got the current files in dropbox

        # if not then we need to list the dropbox folder to find out what the
        # current state is.

        # get cursor or None if it is not set
        cursor = self._get_cursor()

        if cursor:
            # we have a cursor
            # let's check the database to ensure we have some
            log.debug('cursor: ' + cursor)
            pass
        else:
            # missing cursor so we need to list files in dropbox and save to
            # the database.
            log.debug('missing cursor')

            # list all files in dropbox
            entries, cursor = self._get_result_entries(
                cursor, path=settings.DROPBOX_EXPORT_FOLDER, recursive=True)

            for e in entries:
                log.debug(e.path_lower)
                log.debug(pformat(e))

            # save the cursor
            self._save_cursor(cursor)
        

    def shutdown(self):
        self._delete_cursor()


    def get_new_import_files(self, data):
        """Gets recently changed data export files from Dropbox."""

        cursor = self._get_cursor()
        if not cursor:
            log.error('Missing Dropbox cursor. Unable to list changed files.')
            log.error('Running startup process to init cursor.')
            self.startup()
            return

        log.debug('cursor: ' + cursor)

        entries, cursor = self._get_result_entries(
            cursor, path=settings.DROPBOX_EXPORT_FOLDER, recursive=True)

        self._save_cursor(cursor)

        files_to_import = []

        for e in entries:
            log.debug(e.path_lower)

            # Only want the new files, skip folders and deleted file entries.
            if type(e) != dropbox.files.FileMetadata:
                continue

            # get the import type and company name
            try:
                company_name, export_type = self.parse_company_export_type(e.name)
            except ValueError as e:
                # if the company/type is not found this is not an export
                # file. These files should not be added to the export
                # folder.
                log.warning(e)
                continue

            files_to_import.append({'company': company_name,
                                    'export_type': export_type,
                                    'id': e.id})
            
        return files_to_import


    def parse_company_export_type(cls, filename):
        """Parse the company and export_type from filename."""

        type_company_pattern = re.compile(
            r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.(?i)CSV$')

        match = type_company_pattern.match(filename)
        if match:
            company = match.group(2)
            export_type = match.group(1)
            return (company, export_type)
        else:
            raise ValueError(
                'Company or export type not found in filename: {}'
                .format(filename))
