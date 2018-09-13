import os.path

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
