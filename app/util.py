import os.path
import smtplib
from config import config
from email.mime.text import MIMEText


def get_zipfile_from_job_id(job_id):
    return os.path.join(config['Tasks']['workdir'], job_id+'.zip')

def location_to_str(lon, lat):
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

def send_email(to, subject, message, server_settings):
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
