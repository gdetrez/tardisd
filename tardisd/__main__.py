from .backup import BackupChain
from optparse import OptionParser
from IPython import embed
from tardisd.conf import settings
from datetime import datetime, timedelta
import ConfigParser
import logging
import os, sys

EXCLUDE = [ 
    "/home/.ecryptfs/",
    "/home/*/.gvfs/",
    "/home/*/.cache/",
    "/bin/",
    "/boot/",
    "/cdrom/",
    "/dev/",
    "/initrd.img",
    "/initrd.img.old",
    "/lib/",
    "/lost+found/",
    "/media/",
    "/mnt/",
    "/opt/",
    "/proc/",
    "/root/",
    "/run/",
    "/sbin/",
    "/selinux/",
    "/srv/",
    "/sys/",
    "/tmp/",
    "/usr/",
    "/var/",
    "/vmlinuz",
    "/vmlinuz.old",
    ]

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="write report to FILE", metavar="FILE")
    parser.add_option("-q", "--quiet",
                      action="store_const", dest="loglevel",
                      const=logging.WARN, default=logging.INFO,
                      help="don't print status messages to stdout")
    parser.add_option("-v", "--verbose",
                      action="store_const", dest="loglevel", const=logging.DEBUG,
                      help="Print debug informations on stdout")
    parser.add_option("-n", "--dry-run",
                      action="store_true", dest="dry", default=False,
                      help="No Action: show what files would have been copied.")
    parser.add_option("-b", "--backup",
                      action="store", dest="backup", default=None, metavar="NAME",
                      help="Only run NAME backup")

    (options, args) = parser.parse_args()

    logging.basicConfig(level=options.loglevel)

    for name in settings.BACKUP_CHAINS:
        if options.backup is not None and name != options.backup:
            continue
        source = settings.BACKUP_CHAINS[name]["source"]
        destination = settings.BACKUP_CHAINS[name]["destination"]
        exclude = settings.BACKUP_CHAINS[name]["exclude"]
    
        if os.path.exists(source) and os.path.exists(destination):
            logging.info("** Backup: %s **" % name)
            logging.info("Source: %s ; Destination: %s" % (source, destination))
            bc = BackupChain(name, source, destination, exclude)
            logging.info("Found %d old backup" % len(bc.history))
            logging.info("Latest backup: %s" % bc.latest_backup())
            if bc.latest_backup() is None or datetime.now() - bc.latest_backup().when > timedelta(minutes=60):
                logging.info("Previous bckup more than 60 minutes old, backing up again")
                if options.dry:
                    bc.dry_run()
                else:
                    bc.make_backup()
            else:
                logging.info("Previous backup less than 60 minutes old, skipping")
