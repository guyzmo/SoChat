from setuptools import setup
import os
import sys


def read(*names):
    values = dict()
    for name in names:
        if os.path.isfile(name):
            value = open(name).read()
        else:
            value = ''
        values[name] = value
    return values

long_description = """

%(README.md)s

""" % read('README.md')

setup(name='SOChat',
      version='0.1',
      description="Stack Overflow Chat exposed as an IRC Server",
      long_description=long_description,
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: Unix',
      ],
      keywords='stackoverflow api openid irc server chat',
      author='Bernard `Guyzmo` Pratz',
      author_email='stackoverflow@m0g.net',
      url='http://m0g.net',
      license='GPLv3',
      packages=['sochat'],
      zip_safe=False,
      data_files=[('config', ['etc/so-config.ini'])],
      install_requires=[
          'twisted',
          'pystackoverflow',
          'argparse',
          'setuptools',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      soirc_server = sochat.sochat:run
      """,
      )

if "install" in sys.argv:
    print """
Stack Overflow chat as IRC Server is now installed!
"""
