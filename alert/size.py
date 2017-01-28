from __future__ import division

import os
import argparse

from mail import send_ses

FROM_ADDR = "telemetry-alerts@mozilla.com"
EMAIL_SUBJECT = "EFS Directory Too Large!"
EMAIL_BODY = ("Attention, your EFS directory has exceeded the allowed quota. "
              "You are allowed {}, but have stored {}. "
              "Please remove at least {}, or we will have to remove your account.")
ROUNDING = 1

def _get_dirs(directory, depth):
    """Get list of directories at depth from given directory"""
    directories = []
    directory_depth = directory.rstrip(os.path.sep).count(os.path.sep)
    for path, dirs, files in os.walk(directory):
        cur_depth = path.count(os.path.sep)
        if (cur_depth + 1) - directory_depth == depth:
            abs_path = os.path.abspath(path)
            directories += [os.path.join(abs_path, d) for d in dirs]
    return directories 

def _get_dir_size(directory):
    """Get directory size in Bytes"""
    total_size = 0
    for path, dirs, files in os.walk(directory):
        for f in files:
            fp = os.path.join(path, f)
            total_size += os.path.getsize(fp)
    return total_size

def _get_readable_size(size_in_bytes):
    """Max out at 1024YB (future proof! Get at me, EFS!)"""
    for unit in ['','K','M','G','T','P','E','Z','Y']:
        if abs(size_in_bytes) < 1024:
            return '{}{}{}'.format(round(size_in_bytes, ROUNDING), unit, 'B')
        size_in_bytes /= 1024
    return None

def _email_users(to_email, dry_run):
    # TODO: Add other options for getting user's email
    for directory, size, max_size in to_email:
        _, email = os.path.split(directory)
        email_body = EMAIL_BODY.format( _get_readable_size(max_size),
                                        _get_readable_size(size),
                                        _get_readable_size(size - max_size))
        if dry_run:
            print ("\n\nSending Email to {}\n"
                  "From: {}\n"
                  "Subject: {}\n"
                  "Body: {}\n").format(email, FROM_ADDR, EMAIL_SUBJECT, email_body)
        else:
            send_ses(FROM_ADDR, EMAIL_SUBJECT, email_body, email)

def _check_sizes(directory, depth, max_size, dry_run):
    to_email = []

    for check_dir in _get_dirs(directory, depth):
        size = _get_dir_size(check_dir)
        if size > max_size:
            to_email.append((check_dir, size, max_size))

    _email_users(to_email, dry_run)
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EFS Metered Size Alert System',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('directory', type=str,
                        help='Directory in which to check sizes')

    parser.add_argument('--max-size', type=int, default=1024*1024*1024,
                        help='Maximum allowed size of a directory, in Bytes')

    parser.add_argument('--depth', '-d', type=int, default=1,
                        help='Directories at this depth from `EFS-Directory` will be checked')

    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='If True, emails to users will not be sent, but results printed to screen')

    args = parser.parse_args()

    _check_sizes(args.directory, args.depth, args.max_size, args.dry_run)
