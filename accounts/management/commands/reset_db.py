import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Delete everything in the database, for testing and development."

    def handle(self, *args, **options):
        #Remove db
        if os.path.exists('db.sqlite3'):
            os.remove('db.sqlite3')
        #Remove migrations
        for root, dirs, files in os.walk('.',topdown=True):
            if 'migrations' in dirs:
                for file in os.listdir(os.path.join(root, 'migrations')):
                    if "venv" not in root and file.endswith('.py') and file != '__init__.py':
                        os.remove(os.path.join(root, 'migrations', file))
        #Migrations
        os.system('python manage.py makemigrations')
        os.system('python manage.py migrate')