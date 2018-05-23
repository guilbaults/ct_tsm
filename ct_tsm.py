#!/usr/bin/python
import argparse
import logging
import xattr
import uuid
import tsm.client
import sys

"""
Use the Python TSM library from bbrauns/tsm-api-client
https://github.com/bbrauns/tsm-api-client

Each file is assigned a UUID and this reference is used to put the object
in the TSM backend.
"""

logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument('--fd', type=int)
parser.add_argument('--fid', required=True)
parser.add_argument("--lustre-root", required=True)

group_action = parser.add_mutually_exclusive_group(required=True)
group_action.add_argument('--archive', action='store_true')
group_action.add_argument('--restore', action='store_true')
group_action.add_argument('--remove', action='store_true')

parser.add_argument('--verbose', '-v', action='count')

args = parser.parse_args()

tsm_client = tsm.client.TSMApiClient()


def fid2lupath(lustre_root, fid):
    return "{lustre_root}/.lustre/fid/{fid}".format(
        lustre_root=args.lustre_root,
        fid=args.fid.strip('[]'),
    )


if args.archive:
    if args.fd is None:
        logging.error('Need a FD handle to archive a file')
        sys.exit(1)

    fid_path = fid2lupath(args.lustre_root, args.fid)
    logging.debug('Archiving fid %s, with fid_path %s', args.fid, fid_path)

    if 'trusted.lhsm.uuid' in xattr.listxattr(fid_path):
        # Get the previous UUID
        file_uuid = xattr.getxattr(fid_path, 'trusted.lhsm.uuid')
    else:
        # Create a new UUID for a new file
        new_uuid = str(uuid.uuid1()).encode()
        logging.debug('Assigning uuid %s', new_uuid)
        xattr.setxattr(fid_path, 'trusted.lhsm.uuid', new_uuid)
        file_uuid = new_uuid

    tsm_client.archive(filename="/proc/self/fd/{fd}".format(fd=args.fd),
                       filespace='project',
                       highlevel='by-uuid',
                       lowlevel=file_uuid.decode())

if args.restore:
    if args.fd is None:
        logging.error('Need a FD handle to restore a file')
        sys.exit(1)
    fid_path = fid2lupath(args.lustre_root, args.fid)
    logging.debug('Restoring fid %s, with fid_path %s', args.fid, fid_path)
    file_uuid = xattr.getxattr(fid_path, 'trusted.lhsm.uuid')
    logging.debug('UUID: %s', file_uuid.decode())

    tsm_client.retrieve(dest_file="/proc/self/fd/{fd}".format(fd=args.fd),
                        filespace='project',
                        highlevel='by-uuid',
                        lowlevel=file_uuid.decode())

if args.remove:
    logging.debug('Removing fid %s', args.fid)
    # TODO
