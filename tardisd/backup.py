import datetime
import sys, os, shutil, re
import dateutil.parser
import logging
import subprocess
#
# >> tardisd.log 2>&1
#

BKP_LOCATION = "/media/Backup/backup/Soyuz"
BKP_PARTIAL = os.path.join(BKP_LOCATION, ".part")

def rsync(source, destination, excludes=[]):
    command = ["rsync","--archive", "--delete-excluded"]
    for e in excludes:
        command += ["--exclude", e]
    command += [source, destination]
    logging.info("Starting rsync: %s" % command)
    status = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert status == 0, "Rsync exited with non zero status: %d" % status

                       # --exclude "/home/.ecryptfs/" \
                       # --exclude "/home/*/.gvfs/" \
                       # --exclude "/home/*/.cache/" \
                       # --include "/home**" \
                       # --include "/etc**" \                        --exclude "*" \
                       #     / %s""" % (BKP_PARTIAL)

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
        if not os.path.exists(self.partial_backup_path):
            if self.latest_backup() is None:
                os.mkdir(self.partial_backup_path)
            else:
                copytree(self.latest_backup().path, self.partial_backup_path)
        b = Backup(self.destination)
        assert not b.iscomplete(), "Backup complete! [%s]" % b.path
        rsync(self.source, self.partial_backup_path, self.exclude)
        shutil.move(self.partial_backup_path, b.path)
        self.refresh_history()
        return b

class TardisDaemon:

    def __init__(self):
        self.rsyncp = None
        self.history = []
        self.refresh_history()
        logging.info("Found %d old backup" % len(self.history))
        logging.info("Latest backup: %s" % self.latest_backup())

    def refresh_history(self):
        history = []
        for d in os.listdir(BKP_LOCATION):
            try:
                history.append(Backup(dateutil.parser.parse(d)))
            except ValueError:
                if d == ".part":
                    logging.info("Found one incomplete backup")
                else:
                    logging.warning("Unknown file %s in backup location" % d)

        self.history = sorted(history, key=lambda b: b.when, reverse=True)
        

    def latest_backup(self):
        if len(self.history) < 1:
            return None
        return self.history[0]

    def make_backup(self):
        if not os.path.exists(BKP_PARTIAL):
            if self.latest_backup() is None:
                os.mkdir(BKP_PARTIAL)
            else:
                copytree(self.latest_backup().path, BKP_PARTIAL)
        b = Backup()
        b.run()
        
def copytree(src, dst):
    """A special version of copytree, from the shutil module, 
    where hardlink are used instead of actually copying the files."""
    names = os.listdir(src)
    os.makedirs(dst)
    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.islink(srcname):
                os.link(srcname, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname)
            else:
                os.link(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Exception, err:
            errors.extend(err.args[0])
    shutil.copystat(src, dst)
    if errors:
        print errors
        assert False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    tardisd = TardisDaemon()
    tardisd.make_backup()
