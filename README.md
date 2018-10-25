**Tunnel Manager version 0.7.7.2**

by Brandon Williams <opensource@subakutty.net>

This is a python program that helps me to manage the SSH tunnels that I
use regularly for secure remote connectivity to my office and home networks.

The program allows you to maintain a configuration of commonly used
dynamic and/or local SSH port-forwarding tunnels, along with the SSH
keys that the tunnels require. 

The program assumes that you are using key-based SSH authentication for all of
your tunnels (you are, aren't you? if not, then why not?). It also assumes
that you already run an ssh agent that the program can access/manage.

Currently, the program assumes that you are running it on a Unix system with
the various ssh executables located under /usr/bin/.

The program provides command line options that make it suitable as an
autostarted application to load SSH keys and start your tunnels when you log
in to an graphical user session. See tunnelmanager -h or the tunnelmanager
manual page for more information.

Please report all bugs to https://bugs.launchpad.net/tunnelmanager/
