'''
Utility methods for the TAMSAT ALERT webapp
'''

import os.path
import smtplib
from config import config
from email.mime.text import MIMEText


def get_zipfile_from_job_id(job_id):
    '''
    Gets the path of the zipfile associated with a particular job ID

    :param job_id:  The job ID
    :return:        The path, as a string, of the requested zip file
    '''
    return os.path.join(config['Tasks']['workdir'], job_id+'.zip')

def location_to_str(lon, lat):
    '''
    Converts a lon/lat position to a string

    :param lon: The longitude
    :param lat: The latitude
    :return:    A formatted string
    '''
    location_name = ''
    if(lat >= 0):
        location_name += '{0:.3f}°N'.format(lat)
    else:
        location_name += '{0:.3f}°S'.format(-lat)
    location_name += ', '
    if(lon >= 0):
        location_name += '{0:.3f}°E'.format(lon)
    else:
        location_name += '{0:.3f}°W'.format(-lon)
    return location_name

def send_email(to, subject, message):
    '''
    Sends an email

    :param to:              The email address to send to
    :param subject:         The subject of the message
    :param message:         The message
    '''
    server_settings = config['Email']

    # Construct the message
    msg = MIMEText(message)
    msg['To'] = to
    msg['From'] = server_settings['contact']
    msg['Subject'] = subject

    # Send the message
    s = smtplib.SMTP(server_settings['server'])
    s.login(server_settings['username'], server_settings['password'])
    s.send_message(msg)
    s.quit()
