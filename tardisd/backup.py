import datetime
import sys, os, shutil, re
import dateutil.parser
import logging
log = logging.getLogger(__name__)
import subprocess
import tempfile
from .util import rsync, copytree
from tardisd.conf import settings



class Backup:
    def __init__(self, root,  when=None):
        if when is None:
            self.when = datetime.datetime.now()
        else:
            self.when = when
        self.path = os.path.join(root, self.when.isoformat())

    def iscomplete(self):
        return os.path.exists(self.path)

    def __repr__(self):
        return repr(self.when)

    def __unicode__(self):
        return self.when.strftime("%Y-%m-%d, %H:%M")

    def __str__(self):
        return self.__unicode__()


class BackupChain:
    def __init__(self, name, source, destination, exclude=[]):
        self.name = name
        assert os.path.exists(source)
        assert os.path.exists(destination)
        self.source = source
        self.destination = os.path.join(destination, name)
        if not os.path.exists(self.destination):
            os.mkdir(self.destination)
        self.history = []
        self.refresh_history()
        self.partial_backup_path = os.path.join(self.destination, ".part")
        self.exclude = exclude

    def refresh_history(self):
        history = []
        for d in os.listdir(self.destination):
            try:
                history.append(Backup(self.destination, dateutil.parser.parse(d)))
            except ValueError:
                if d == ".part":
                    logging.info("Found one incomplete backup")
                else:
                    logging.warning("Unknown file %s in backup location" % d)

        self.history = sorted(history, key=lambda b: b.when)

    def latest_backup(self):
        if len(self.history) < 1:
            return None
        return self.history[-1]

    def make_backup(self):
        log.info("Backup started")
        if not os.path.exists(self.partial_backup_path):
            if self.latest_backup() is None:
                os.mkdir(self.partial_backup_path)
            else:
                copytree(self.latest_backup().path, self.partial_backup_path)
        b = Backup(self.destination)
        assert not b.iscomplete(), "Backup complete! [%s]" % b.path
        assert os.path.isdir(settings.LOG_DIR)
        rsync(self.source, self.partial_backup_path, self.exclude, logfile=os.path.join("/var/log/tardisd/rsynclog-%s-%s" % (self.name, b.when.isoformat())))
        shutil.move(self.partial_backup_path, b.path)
        self.refresh_history()
        return b

    def dry_run(self):
        delete_dest_after = False
        dest = ""
        if os.path.exists(self.partial_backup_path):
            dest = self.partial_backup_path
        elif self.latest_backup() is not None:
            dest = self.latest_backup().path
        else:
            dest = tempfile.mkdtemp()
            delete_dest_after = True
        rsync(self.source, dest, self.exclude, dry=True)
        if delete_dest_after:
            os.rmdir(dest)
