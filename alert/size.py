from __future__ import division

import os
import argparse
import boto3

from mail import send_ses

TELEMETRY_ADDR = 'telemetry-alerts@mozilla.com'
DEV_TELEMETRY_ADDR = 'dev-telemetry-alerts@mozilla.com'

EMAIL_SUBJECT = 'ACTION NEEDED: EFS Exceeds Allowed Size'
EMAIL_BODY = ('EFS file system {} has exceeded the allowed size of {}. '
              'It is currently at {}.')

USER_EMAIL_SUBJECT = 'EFS Directory Too Large!'
USER_EMAIL_BODY = ('Attention, your EFS directory has exceeded the allowed quota. '
              'You are allowed {}, but have stored {}. '
              'Please remove at least {}, or we will have to remove your account.')

def _get_dirs(directory, depth):
    '''Get list of directories at depth from given directory'''
    directories = []
    directory_depth = directory.rstrip(os.path.sep).count(os.path.sep)
    for path, dirs, files in os.walk(directory):
        cur_depth = path.count(os.path.sep)
        if (cur_depth + 1) - directory_depth == depth:
            abs_path = os.path.abspath(path)
            directories += [os.path.join(abs_path, d) for d in dirs]
    return directories 

def _get_dir_size(directory):
    '''Get directory size in Bytes'''
    total_size = 0
    for path, dirs, files in os.walk(directory):
        for f in files:
            fp = os.path.join(path, f)
            total_size += os.path.getsize(fp)
    return total_size

def _get_readable_size(size_in_bytes, rounding=1):
    '''Max out at 1024YB (future proof! Get at me, EFS!)'''
    for unit in ['','K','M','G','T','P','E','Z','Y']:
        if abs(size_in_bytes) < 1024:
            return '{}{}{}'.format(round(size_in_bytes, rounding), unit, 'B')
        size_in_bytes /= 1024
    return None

def _email_users(to_email, dry_run):
    '''Emails users about the size of their directories.
       This assumes directory names are the user's email'''
    for directory, size, max_size in to_email:
        _, email = os.path.split(directory)
        email_body = USER_EMAIL_BODY.format(_get_readable_size(max_size),
                                            _get_readable_size(size),
                                            _get_readable_size(size - max_size))
        if dry_run:
            print ('\n\nSending Email to {}\n'
                  'From: {}\n'
                  'Subject: {}\n'
                  'Body: {}\n').format(email, TELEMETRY_ADDR, USER_EMAIL_SUBJECT, email_body)
        else:
            send_ses(TELEMETRY_ADDR, USER_EMAIL_SUBJECT, email_body, email)

def _check_sizes(directory, depth, max_size, dry_run):
    '''Checks the sizes of user dirs. Directory must be mounted locally.
       If size of a user dir exceeds max_size, send an email''' 
    to_email = []

    for check_dir in _get_dirs(directory, depth):
        size = _get_dir_size(check_dir)
        if size > max_size:
            to_email.append((check_dir, size, max_size))

    _email_users(to_email, dry_run)

def _get_efs_size(efs_name):
    '''Get the size of an EFS file system, by name'''
    client = boto3.client('efs')
    response = client.describe_file_systems()

    file_systems = response['FileSystems']
    file_system = filter(lambda x: x['Name'] == efs_name, file_systems)

    return file_system[0]['SizeInBytes']['Value']

def _email_size_too_large(efs_name, size, max_size, dry_run):
    '''Emails telemetry-dev know that the EFS file system is too large'''
    email_body = EMAIL_BODY.format(efs_name, 
                                   _get_readable_size(max_size),
                                   _get_readable_size(size))
    if dry_run:
        print ('\n\nSending Email to {}\n'
              'From: {}\n'
              'Subject: {}\n'
              'Body: {}\n').format(DEV_TELEMETRY_ADDR, TELEMETRY_ADDR, USER_EMAIL_SUBJECT, email_body)
    else:
        send_ses(TELEMETRY_ADDR, USER_EMAIL_SUBJECT, email_body, DEV_TELEMETRY_ADDR)


def run_checks(efs_name, max_efs_size, directory, user_depth, user_max_size, dry_run):
    '''Run checks on sizes for EFS file system. First checks the total size, if it exceeds
       some threshold, checks each user's dir to see if it is exceeding our quota.'''
    efs_size = _get_efs_size(efs_name)

    if efs_size > max_efs_size:
        _email_size_too_large(efs_name, efs_size, max_efs_size, dry_run)

        if directory:
            _check_user_sizes(directory, user_depth, user_max_size, dry_run)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EFS Metered Size Alert System',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--efs-name', type=str, required=True,
                        help='Name of EFS file system to check')

    parser.add_argument('--max-size', type=int, required=True,
                        help='Max allowed size of file system')

    parser.add_argument('--efs-dir', type=str, default=None,
                        help='Local directory in which to check sizes (should be where EFS is mounted)')

    parser.add_argument('--max-user-size', type=int, default=1024*1024*1024,
                        help='Maximum allowed size of a directory, in Bytes')

    parser.add_argument('---user-dir-depth', '-d', type=int, default=1,
                        help='Directories at this depth from `EFS-Directory` will be checked')

    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='If True, emails to users will not be sent, but results printed to screen')

    args = parser.parse_args()

    run_checks(args.efs_name, args.max_size, args.efs_dir, args.user_dir_depth, args.max_user_size, args.dry_run)
