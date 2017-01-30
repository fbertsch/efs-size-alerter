from __future__ import division

import os
import boto3

from mail import send_ses


EMAIL_SUBJECT = 'ACTION NEEDED: EFS Exceeds Allowed Size'
EMAIL_BODY = ('EFS file system {} has exceeded the allowed size of {}. '
              'It is currently at {}.')

EMAIL_SUBJECT_USER_LIST = 'List of Users Exceeding EFS Quota'

USER_EMAIL_SUBJECT = 'EFS Directory Too Large!'
USER_EMAIL_BODY = ('Attention, your EFS directory has exceeded the allowed quota. '
                   'You are allowed {}, but have stored {}. '
                   'Please remove at least {}, or we will have to remove your account.')


def run_checks(efs_name, max_efs_size, from_email, to_email,
               directory=None, user_depth=1, user_max_size=None,
               email_users=False, dry_run=False):
    '''Run checks on sizes for EFS file system. First checks the total size, if it exceeds
       some threshold, then optionally checks each user's dir to see if it is exceeding a quota.

       If directory is None, the user directories will not be checked for size limits.

       param efs_name: The name of the EFS file system to check
       param max_efs_size: The max allowed size of the file system
       param from_email: Email address alert emails are sent from
       param to_email: Email address alert emails are sent to
       param directory: Local path to where this EFS file system is mounted (default: None)
       param user_depth: Depth of user directories from mounted directory (default: 1)
       param user_max_size: Max size of a user directory (default: max_efs_size)
       param email_user: Boolean, whether to email users about size violations (default: False)
       param dry_run: If True, email will not be sent, but printed to the screen (default: False)
    '''
    if user_max_size is None:
        user_max_size = max_efs_size

    efs_size = _get_efs_size(efs_name)

    if efs_size > max_efs_size:
        _email_size_too_large(from_email, to_email, efs_name, efs_size, max_efs_size, dry_run)

    if directory:
        _check_user_sizes(directory, user_depth, user_max_size, from_email,
                          to_email, email_users, dry_run)


###### Private Functions #######


def _get_efs_size(efs_name):
    '''Get the size of an EFS file system, by name'''
    client = boto3.client('efs')
    response = client.describe_file_systems()

    file_systems = response['FileSystems']
    file_system = filter(lambda x: x['Name'] == efs_name, file_systems)

    # TODO: deal with non-unique fs names
    return file_system[0]['SizeInBytes']['Value']


def _email_size_too_large(from_email, to_email, efs_name, size, max_size, dry_run):
    '''Emails that the EFS file system is too large'''
    email_body = EMAIL_BODY.format(efs_name,
                                   _get_readable_size(max_size),
                                   _get_readable_size(size))

    if dry_run:
        _print_email(to_email, from_email, EMAIL_SUBJECT, email_body)
    else:
        send_ses(from_email, USER_EMAIL_SUBJECT, email_body, to_email)


def _check_user_sizes(directory, depth, max_size, from_email, to_email, email_users, dry_run):
    '''Checks the sizes of user dirs. Directory must be mounted locally.
       If size of a user dir exceeds max_size, send an email'''
    invalid_users = []

    for check_dir in _get_dirs(directory, depth):
        size = _get_dir_size(check_dir)
        if size > max_size:
            invalid_users.append((check_dir, size, max_size))

    if invalid_users:
        _email_about_users(invalid_users, max_size, from_email, to_email, dry_run)
        if email_users:
            _email_users(invalid_users, max_size, from_email, to_email, dry_run)


def _get_dirs(directory, depth):
    '''Get list of directories at depth from given directory'''
    directories = set()
    directory_depth = directory.rstrip(os.path.sep).count(os.path.sep)
    for path, dirs, files in os.walk(directory):
        cur_depth = path.rstrip(os.path.sep).count(os.path.sep)
        if (cur_depth + 1) - directory_depth == depth:
            abs_path = os.path.abspath(path)
            directories |= set([os.path.join(abs_path, d) for d in dirs])
    return directories


def _get_dir_size(directory):
    '''Get directory size in Bytes'''
    total_size = 0
    for path, dirs, files in os.walk(directory):
        for f in files:
            fp = os.path.join(path, f)
            total_size += os.path.getsize(fp)
    return total_size


def _email_about_users(invalid_users, max_size, from_email, to_email, dry_run):
    '''Emails the list of users who are exceeding quota'''
    email_body = '\n'.join(('{}: {}, Quota: {}'.format(directory,
                                                       _get_readable_size(size),
                                                       _get_readable_size(max_size))
                            for directory, size, max_size in invalid_users))
    if dry_run:
        _print_email(to_email, from_email, EMAIL_SUBJECT_USER_LIST, email_body)
    else:
        send_ses(from_email, EMAIL_SUBJECT_USER_LIST, email_body, to_email)


def _email_users(invalid_users, max_size, from_email, to_email, dry_run):
    '''Emails users about the size of their directories.
       This assumes directory names are the user's email'''
    for directory, size, max_size in invalid_users:
        _, email = os.path.split(directory)
        email_body = USER_EMAIL_BODY.format(_get_readable_size(max_size),
                                            _get_readable_size(size),
                                            _get_readable_size(size - max_size))
        if dry_run:
            _print_email(email, from_email, USER_EMAIL_SUBJECT, email_body)
        else:
            send_ses(from_email, USER_EMAIL_SUBJECT, email_body, email)


##### Utility Functions #######


def _get_readable_size(size_in_bytes, rounding=1):
    '''Max out at 1024YB (future proof! Get at me, EFS!)'''
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
        if abs(size_in_bytes) < 1024:
            return '{}{}{}'.format(round(size_in_bytes, rounding), unit, 'B')
        size_in_bytes /= 1024
    return None


def _print_email(to, _from, subject, body):
    print ('\n\nSending Email to {}\n'
           'From: {}\n'
           'Subject: {}\n'
           'Body: {}\n').format(to, _from, subject, body)
