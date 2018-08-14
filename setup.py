#!/usr/bin/env python

from distutils.core import setup;

setup(name='tunnelmanager',
      version='0.7.7.2',
      description='TunnelManager -- SSH Tunnel Manager',
      author='Brandon Williams',
      author_email='opensource@subakutty.net',
      url='http://www.subakutty.net/tunnelmanager/',
      license='GPL v2',

      packages=['TunnelManager'],
      scripts=['tunnelmanager','tunnelrunner','tunnelmanager_cli','tunnelrunner_askpass'],
      data_files=[('share/applications', ['data/tunnelmanager.desktop']),
                  ('share/man/man1', ['doc/tunnelmanager.1']),
                  ('share/man/man1', ['doc/tunnelmanager_cli.1']),
                  ('share/man/man1', ['doc/tunnelrunner.1']),
                  ('share/man/man1', ['doc/tunnelrunner_askpass.1']),
                  ('share/tunnelmanager', ['data/tunnelmanager.ui']),
                  ('share/locale/cs/LC_MESSAGES', ['msg/cs/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/da/LC_MESSAGES', ['msg/da/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/de/LC_MESSAGES', ['msg/de/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/en/LC_MESSAGES', ['msg/en/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/es/LC_MESSAGES', ['msg/es/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/id/LC_MESSAGES', ['msg/id/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/it/LC_MESSAGES', ['msg/it/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/pl/LC_MESSAGES', ['msg/pl/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/pt_BR/LC_MESSAGES', ['msg/pt_BR/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/ru/LC_MESSAGES', ['msg/ru/LC_MESSAGES/tunnelmanager.mo']),
                  ('share/locale/zh_CN/LC_MESSAGES', ['msg/zh_CN/LC_MESSAGES/tunnelmanager.mo']),
                 ],
     );
