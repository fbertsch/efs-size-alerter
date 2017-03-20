from setuptools import setup

setup(name='efs-size-alerter',
      version='0.0.2',
      author='Frank Bertsch',
      author_email='fbertsch@mozilla.com',
      description='Email User\'s when their EFS directories exceed a quota',
      url='https://github.com/fbertsch/efs-size-alerter',
      packages=['alert'],
      install_requires=['boto', 'boto3'],
      scripts=['check-size'])
