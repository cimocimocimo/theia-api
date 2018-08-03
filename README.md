# JS Group Inventory Update Script

This script takes the inventory spreadsheets and updates all the Shopify stores with their data.

## Process

1. Spreadsheet files are exported to Dropbox from Momentis.
2. Dropbox calls the webhook for each of the exported files.
3. The app listens for the webhook call to /webhook/dropbox-updated
4. The webhook calls a view that then processes the changed file and imports it's data into redis
5. The redis data is then imported to Shopify.

The webhook calls a celery task to import the file data and perform the export to shopify on a per file basis.

## Development

The Celery worker needs to be running to run tasks

To respond to the dropbox calls to the webhook:

1. start ngrok with this command.

$ ngrok http 8000

2. start django server.

$ ./manage.py runserver

3. start celery worker:

$ celery worker -A core -l debug

If you want to trigger dropbox webhook calls. update the development dropbox account app.

1. Log into dropbox and update the development app. Add the ngrok url as a webhook and add '/webhook/dropbox-updated/' to the url. The final trailing slash is important, if it is not there the app will not verify since it will receive a 301 redirect response from the Django server.

ie: http://

ie: http://5d3e5468.ngrok.io/webhook/dropbox-updated

note: the hash in the url will be unique for every run of ngrok.

### Setup Dropbox webhook

1. create dropbox app in target account, this requires full access for production since the export folder already exists. If you are develoing, then we can just use a folder based app for testing.
2. Generate the access token, copy it and the App key and App secret.
3. Save them to these local environment variables for development: DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_TOKEN
4. If this is for the production environment then save them in ./.ebextensions/02_environment-vars-secret.config
5. Add webhook by copying the ngrok endpoint url or the Beanstalk URL with the path 'webhook/dropbox-updated/'. The trailing slash is important. The ngrok url will need to be updated everytime it's started on the development machine.






