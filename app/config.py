import configparser

config = configparser.ConfigParser()
# Set up default options, in case they are missing from the file
config['Tasks'] = {'workdir': '/tmp/tamsat-alert',
                   'dbfile': '/tmp/tamsat-alert/ta-jobs.sqlite3',
                   'days_to_keep_completed': '7',
                   'hours_to_keep_downloaded': '24'
                   }
config['Email'] = {'server': 'smtp.reading.ac.uk',
                   'contact': 'tamsat@reading.ac.uk',
                   'username': 'CHANGEME',
                   'password': 'CHANGEME'
                   }
config['Data'] = {'path': '/configure/path/to/data',
                  'climatology_start_year': '1983',
                  'climatology_end_year': '2010',
                  'period_of_interest_start_year': '1983',
                  'period_of_interest_end_year': '2010'
                  }
config['Celery'] = {'backend': 'redis://',
                    'broker': 'redis://'}


# Read the config file.  This will overwrite any defaults
config.read('tamsat-alert.cfg')
