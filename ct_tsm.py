#!/usr/bin/python
import argparse
import logging
import xattr
import uuid
import tsm.client
import sys
import time
import os.path
import configparser
import pymysql

"""
Use the Python TSM library from bbrauns/tsm-api-client
https://github.com/bbrauns/tsm-api-client

Each file is assigned a UUID and this reference is used to put the object
in the TSM backend.
"""

logging.basicConfig(level=logging.DEBUG)

# Overwrite the default log level for TSM client. It is very verbose and
# causes problems with systemd as this is all STDOUT
tsmlogger = logging.getLogger('tsm.client')
tsmlogger.propagate = False
tsmlogger.setLevel(logging.DEBUG)


parser = argparse.ArgumentParser()
parser.add_argument('--fd', type=int)
parser.add_argument('--fid', required=True)
parser.add_argument("--lustre-root", required=True)
parser.add_argument("--filespace", default='project', type=str,
                    help="TSM filespace where the archived file is stored, \
should be similair to the Lustre filesystem name")
parser.add_argument("--config", default='/etc/lhsm_cmd.conf', type=str,
                    help="Config file, required to get the information in \
the database of robinhood to remove with uuid")

group_action = parser.add_mutually_exclusive_group(required=True)
group_action.add_argument('--archive', action='store_true',
                          help="Send this file to TSM")
group_action.add_argument('--restore', action='store_true',
                          help="Retrieve the content from TSM")
group_action.add_argument('--remove', action='store_true',
                          help="Delete this file from TSM")

parser.add_argument('--verbose', '-v', action='count')

args = parser.parse_args()

tsm_client = tsm.client.TSMApiClient()


def fid2lupath(lustre_root, fid):
    return "{lustre_root}/.lustre/fid/{fid}".format(
        lustre_root=args.lustre_root,
        fid=args.fid.strip('[]'),
    )


def logstatus(action, status, time, fid, size=0):
    logging.info(
        'type=stats fid={0} action={1} status={2} runtime={3} size={4}'.format(
             fid, action, status, time, size))


start = time.time()
if args.archive:
    action = 'ARCHIVE'
    if args.fd is None:
        logging.error('Need a FD handle to archive a file')
        sys.exit(1)
    if os.path.isfile("/proc/self/fd/{0}".format(args.fd)) is False:
        logging.error('FD does not exist')
        sys.exit(1)

    fid_path = fid2lupath(args.lustre_root, args.fid)
    logging.info('Archiving fid %s, with fid_path %s', args.fid, fid_path)

    if 'trusted.lhsm.uuid' in xattr.listxattr(fid_path):
        # Get the previous UUID
        file_uuid = xattr.getxattr(fid_path, 'trusted.lhsm.uuid')
    else:
        # Create a new UUID for a new file
        new_uuid = str(uuid.uuid1()).encode()
        logging.debug('Assigning uuid %s', new_uuid)
        xattr.setxattr(fid_path, 'trusted.lhsm.uuid', new_uuid)
        file_uuid = new_uuid
    try:
        logging.debug('Starting Archival call: tsm_client.archive')
        tsm_client.archive(filename="/proc/self/fd/{fd}".format(fd=args.fd),
                           filespace=args.filespace,
                           highlevel='by-uuid',
                           lowlevel=file_uuid.decode())
        logging.info('Archive complete for {}'.format(args.fid))
        status = 'SUCCESS'
    except Exception as e:
        status = 'FAILURE'
        logging.error(e)
    finally:
        tsm_client.close()

if args.restore:
    action = 'RESTORE'
    if args.fd is None:
        logging.error('Need a FD handle to restore a file')
        sys.exit(1)
    fid_path = fid2lupath(args.lustre_root, args.fid)
    logging.info('Started restore of fid %s, with fid_path %s',
                 args.fid, fid_path)
    file_uuid = xattr.getxattr(fid_path, 'trusted.lhsm.uuid')
    logging.debug('UUID: %s', file_uuid.decode())

    try:
        tsm_client.connect()
        tsm_client.retrieve(dest_file="/proc/self/fd/{fd}".format(fd=args.fd),
                            filespace=args.filespace,
                            highlevel='by-uuid',
                            lowlevel=file_uuid.decode())
        logging.info('Retreival of fid {} from TSM completed'.format(args.fid))
        status = 'SUCCESS'
    except Exception as e:
        status = 'FAILURE'
        logging.error(e)
    finally:
        tsm_client.close()

if args.remove:
    action = 'REMOVE'
    logging.info('Started removal of fid {} from TSM'.format(args.fid))
    fid_path = fid2lupath(args.lustre_root, args.fid)
    try:
        file_uuid = xattr.getxattr(fid_path, 'trusted.lhsm.uuid')
    except IOError:
        # File does not exist, we need to check in robinhood to get the UUID
        # in the SOFT_RM table
        config = configparser.ConfigParser()
        config.read(args.config)
        db = pymysql.connect(
            config.get('database', 'host'),
            config.get('database', 'user'),
            config.get('database', 'password'),
            config.get('database', 'db'))
        cursor = db.cursor()
        query = "SELECT lhsm_uuid FROM SOFT_RM_DELAYED \
WHERE id=\"{fid}\"".format(
            fid=args.fid.strip("[]"))
        cursor.execute(query)
        file_uuid = cursor.fetchone()[0]

    logging.debug('UUID: %s', file_uuid.decode())
    try:
        tsm_client.connect()
        tsm_client.delete(filespace=args.filespace,
                          highlevel='by-uuid',
                          lowlevel=file_uuid.decode())
        logging.info('Deletion of fid {} from TSM completed'.format(args.fid))
        status = 'SUCCESS'
    except Exception as e:
        logging.error(e)
        status = 'FAILURE'
    finally:
        tsm_client.close()

runtime = round(time.time() - start)
logstatus(action, status, runtime, args.fid)
if status != 'SUCCESS':
    sys.exit(1)
