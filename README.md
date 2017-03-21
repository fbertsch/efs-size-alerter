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

2. Assume the file system is mounted at `/Users/frankbertsch/repos/sandbox/test`

3. Check for any user accounts at 1 level deep, and if they exceed 100B, emails the User from `from@moz`
Note: This assumes the directory name is the user email

4. Email  `to@moz` from `from@moz` about all user accounts that exceed the quota of 100B

## Common Issues

### No Region Specified

The error `botocore.exceptions.NoRegionError: You must specify a region.` can be resolved by running the following:

```bash
export AWS_DEFAULT_REGION=us-west-2
```

### Access Denied Exception

The resource you are running this on (ec2, presumably) needs access to the EFS resource. Create a policy with `DescribeFileSystems` access and attach it to the ARN or role of the instance you are running on.

## Testing

We recommend running with `--dry-run` to print out emails that would be sent.
