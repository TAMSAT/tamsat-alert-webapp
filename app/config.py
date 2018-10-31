'''
Configuration for the TAMSAT ALERT webapp.

This defines default values, overrides them with the tamsat-alert.cfg
file, and exports that object for use with other modules
'''

import configparser

config = configparser.ConfigParser()
# Set up default options, in case they are missing from the file
config['Tasks'] = {'workdir': '/tmp/tamsat-alert',
                   'dbfile': '/tmp/tamsat-alert/ta-jobs.sqlite3',
                   'days_to_keep_completed': '7',
                   'hours_to_keep_downloaded': '24',
                   'download_link': 'www.tamsat.org.uk/alert/downloadResult'
                   }
config['Email'] = {'server': 'smtp.reading.ac.uk',
                   'contact': 'tamsat@reading.ac.uk',
                   'username': 'CHANGEME',
                   'password': 'CHANGEME'
                   }
config['Data'] = {
'tamsat_path': '/usr/local/tamsat-data/data/v3/daily/**/**/*.nc',
                  'met_fc_temp_path': '/usr/local/tamsat-data/data/NCEP_data/**/air.2m.*.nc',
                  'met_fc_path': '/usr/local/tamsat-data/data/NCEP_data/**/*.nc',
                  'precip_str': 'rfe',
                  'temp_str': 'air',
                  'sw_rad_str': 'dswr',
                  'lw_rad_str': 'dlwr',
                  'pr_str': 'prate',
                  'pressure_str': 'pres',
                  'wind_u_comp_str': 'uwnd',
                  'wind_v_comp_str': 'vwnd',
                  'humidity_str': 'shum',
                  'climatology_start_year': '1983',
                  'climatology_end_year': '2010',
                  'period_of_interest_start_year': '1983',
                  'period_of_interest_end_year': '2010'
                  }
config['Celery'] = {'backend': 'redis://',
                    'broker': 'redis://'}


# Read the config file.  This will overwrite any defaults
config.read('tamsat-alert.cfg')
