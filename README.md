TAMSAT ALERT Webapp
===================

About
-----
This repository contains a Flask + Celery based web application for running code from the [TAMSAT ALERT](https://github.com/TAMSAT/tamsat-alert) repository in a queue system.

The code from TAMSAT ALERT is used as a git submodule, and so before using this repository, you must initialise and download that code using:

```
git submodule update --init
```

The application does the following:

* Presents a web frontend, allowing users to input the required parameters to run TAMSAT ALERT code
* Accepts HTTP POST requests to a backend, which creates a job and submits it to a queue
* Runs jobs asynchronously, finally zipping the output of TAMSAT ALERT, and emailing users with a link to download the data
* Accepts HTTP GET requests to query available data, or to download completed jobs
* Removes completed jobs after a configured period (which may be different depending on whether or not the result has been downloaded)

Running the Application
-----------------------
The configuration for running as a local Docker application is all contained within the root project directory, and consists of 2 `Dockerfile`s and a `docker-compose.yml`.  The application can be started with

```
docker-compose up --build
```

as usual, but should be stopped using:

```
docker-compose stop
```

rather than:

```
docker-compose down
```

since the latter will not wait for queued jobs to be completed.

Code Structure
--------------
The code for the application resides in `./app/`, and the main entrypoint is defined in `./app/main.py`.  The web frontend is contained within `./app/templates` and `./app/static`, depending on whether it consists of dynamic content or not.

All configuration for the application is performed in the `./app/tamsat-alert.cfg` file, and this should be modified prior to deployment to ensure the application functions correctly.  It contains the following sections and parameters:

* [Tasks] - This section is related to running jobs
	- `workdir` - Where the output of jobs should be stored
	- `dbfile` - Where the database storing job state should be stored
	- `days_to_keep_completed` - How many days to keep completed jobs before they are removed
	- `hours_to_keep_downloaded` - How many hours after download to keep jobs before they are removed
* [Email] - This section relates to settings for sending users emails
	- `server` - The SMTP server to use when sending emails
	- `username` - The username for authentication with the SMTP server
	- `password` - The password for authentication with the SMTP server
	- `contact` - The reply address for emails
* [Data] - This section defines parameters associated with the required data
	- `path` - A glob expression defining the location of the data.  If this is a multiple-file dataset, the lexical order of files (including paths) must match their temporal order.
	- `climatology_start_year` - The start year for the climatology parameter to the TAMSAT ALERT code
	- `climatology_end_year` - The end year for the climatology parameter to the TAMSAT ALERT code
	- `period_of_interest_start_year` - The start year for the period of interest parameter to the TAMSAT ALERT code
	- `period_of_interest_end_year` - The end year for the period of interest parameter to the TAMSAT ALERT code
* [Celery] - This section defines parameters for the Celery, and should generally be left alone
	- `backend` - The results backend to use
	- `broker` - The broker to use


Author
------
This tool was developed by [@guygriffiths](https://github.com/guygriffiths) as part of the [TAMSAT](http://www.tamsat.org.uk) project.
