# EFS Size Alerter: Know when your EFS instance is beyond quota

EFS is a great tool, but lacks the simple capability of setting quotas. This little project solves that in a simple way by just checking the size of the file system, and optionally checking the size for each user. If any exceed a given quota, emails are sent out.

## Usage

Type in `check-sizes -h` to get a list of options for the CLI.

Example:
```bash
check-size --efs-name ATMO-prod --max-size 2048 --from-email from@moz --to-email to@moz --efs-dir /Users/frankbertsch/repos/sandbox/test/ --max-user-size 100 --email-users
```

This would:

1. Check if the EFS File System size exceeds 2KB, and email `to@moz` from `from@moz` if so

2. Assumes the file system is mounted at `/Users/frankbertsch/repos/sandbox/test`

3. Checks for any user accounts at 1 level deep, and if they exceed 100B, emails the User from `from@moz`

4. Emails  `to@moz` from `from@moz` about all user accounts that exceed the quota of 100B

## Testing

We recommend running with `--dry-run` to print out emails that would be sent.
