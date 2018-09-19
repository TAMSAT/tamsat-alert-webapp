'''
Factors out code dealing with the SQLite database.
'''

import sqlite3
from config import config
from datetime import timedelta, datetime as dt

def _run_sql(command, values=(), expect_results=False, return_id=False):
    '''
    A convenience method for opening the database, running some SQL,
    committing the result, and closing it again.

    :param command:         The SQL to run
    :param values:          A tuple of values to insert into the SQL statement
    :param expect_results:  Whether the SQL command should return results.
                            Optional, defaults to False
    :param return_id:       Whether the SQL command should return the ID of inserted code.
                            This is mutually exclusive with expect_results, with the
                            former taking precedence.
                            Optional, defaults to False
    :return: A pandas DataFrame containing all variables present in the NetCDF dataset
    '''
    ret = None

    db = sqlite3.connect(config['Tasks']['dbfile'])
    # 'with' takes care of the commit, but doesn't close the DB
    with db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(command, values)
        if expect_results:
            ret = c.fetchall()
        elif return_id:
            ret = c.lastrowid
    db.close()

    return ret

def init():
    '''
    Setup the job list database on first run, if necessary
    '''
    _run_sql('''
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,
            userhash TEXT,
            status TEXT,
            time INTEGER,
            description TEXT,
            job_id TEXT)
    ''')

def add_job(userhash, description):
    return _run_sql('''
        INSERT INTO jobs(userhash, status, time, description) VALUES(?,?,?,?)
    ''',
    (userhash, 'QUEUED', int(dt.now().timestamp()), description), return_id=True)

def set_job_running(db_key, job_id):
    _run_sql('''
        UPDATE jobs SET status=?, time=?, job_id=?
        WHERE id=?
    ''',
    ('RUNNING', int(dt.now().timestamp()), job_id, db_key))

def set_job_completed(db_key):
    _run_sql('''
        UPDATE jobs SET status=?, time=?
        WHERE id=?
    ''',
    ('COMPLETED', int(dt.now().timestamp()), db_key))

def get_jobs(userhash):
    rows = _run_sql('''
        SELECT description, status, time, job_id
        FROM jobs
        WHERE userhash=?
    ''',
    (userhash,),
    True)

    jobs = []
    for row in rows:
        jobs.append({
            'description': row['description'],
            'status': row['status'],
            'time': dt.fromtimestamp(int(row['time'])),
            'job_id': row['job_id']
        })
    return jobs

def set_downloaded(job_id):
    _run_sql('''
                UPDATE jobs SET status=?, time=?
                WHERE job_id=?
            ''',
            ('DOWNLOADED', int(dt.now().timestamp()), job_id))

def set_error(job_id):
    _run_sql('''
                UPDATE jobs SET status=?, time=?
                WHERE job_id=?
            ''',
            ('ERROR', int(dt.now().timestamp()), job_id))

def remove_expired_jobs():
    removed_job_ids=[]

    db = sqlite3.connect(config['Tasks']['dbfile'])
    # 'with' takes care of the commit, but doesn't close the DB
    # Read all of the jobs
    with db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute('''
            SELECT id, status, time, job_id
            FROM jobs
            ''')
        rows = c.fetchall()

        # Find which jobs are expired
        for row in rows:
            time = dt.fromtimestamp(int(row['time']))
            expiry_time_completed = time + \
                timedelta(days=int(config['Tasks']['days_to_keep_completed']))
            expiry_time_downloaded = time + \
                timedelta(hours=int(config['Tasks']['hours_to_keep_downloaded']))
            if (row['status'] == 'COMPLETED' and dt.now() > expiry_time_completed) or \
                    (row['status'] == 'DOWNLOADED' and dt.now() > expiry_time_downloaded):
                removed_job_ids.append(row['job_id'])

                # Remove the entry from the database
                c.execute('''
                    DELETE from jobs WHERE id=?
                ''', (row['id'],))
    db.close()
    return removed_job_ids

# Init database when this module is imported
init()
