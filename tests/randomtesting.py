from tardisd.backup import Backup, BackupChain

import random
import unittest
import datetime
import tempfile
import shutil
import os, sys
import string
from time import sleep
from subprocess import Popen, PIPE
from commands import getstatusoutput as run
import logging


def randdatetime():
    return datetime.datetime.fromtimestamp(random.randrange(2147483648))

def randstring(size):
    ltrs = [random.choice(string.ascii_letters) for i in range(size)]
    return ''.join(ltrs)

def checksum(root, path):
    """Compute a checksum for a file hierarchy"""
    tar = Popen(["tar", "-cf", "-", path], cwd=root, stdout=PIPE, stderr=PIPE)
    md5sum = Popen("md5sum", stdin = tar.stdout, stdout=PIPE)
    assert tar.wait() == 0, "tar error: %s" % tar.stderr.read()
    assert md5sum.wait() == 0, "md5um error"
    return md5sum.stdout.read().split()[0]


class DirectoryTree:
    """ This class can be used to manibulate a directory hierarchy.
    It allows to inspect, pick files and directories at random, 
    perform random changes and compute a checksum of the full 
    structure (including metadatas)"""
    
    def __init__(self, root=None):
        if root is None:
            self.root = tempfile.mkdtemp(prefix="tardis-test")
        else:
            self.root = root

    def checksum(self):
        return checksum(*os.path.split(os.path.normpath(self.root)))
            
    def files(self):
        """List all files in the tree"""
        for dirname, _, files in os.walk(self.root):
            for f in files:
                yield os.path.join(dirname, f)
    
    def random_file(self):
        """Return a random file from the tree"""
        return random.choice(list(self.files()))

    def directories(self, include_root=False):
        """List all the directories in the tree"""
        if include_root:
            yield self.root
        for dirname, subdirs, _ in os.walk(self.root):
            for d in subdirs:
                yield os.path.join(dirname, d)

    def random_directory(self, include_root=False):
        "Return a random directory from the tree"""
        dirlist = list(self.directories(include_root))
        return random.choice(dirlist)

    def make_random_changes(self, nchanges=1):
        actions = [self.add_file,
                   self.change_file,
                   self.rm_file,
                   self.add_dir,
                   self.rm_dir,
                   self.add_symlink]
        [random.choice(actions)() for i in range(nchanges)]

    def add_file(self, path=None):
        if path is None:
            d = self.random_directory(True)
            path = os.path.join(d, randstring(10) + ".txt")
        assert path.startswith(self.root)
        with open(path, "w") as f:
            f.write(randstring(100) + "\n")
        logging.debug("CREATED FILE: %s" % path)

    def change_file(self, path=None, mode=None, content=None):
        if path is None:
            try:
                path = self.random_file()
            except IndexError: # no files
                return
        assert path.startswith(self.root)
        if mode is None:
            mode = random.choice(['a','w'])
        if content is None:
            content = randstring(100) + "\n"
        if not os.path.exists(path):
            return # Broken symbolic link
        with open(path, mode) as f:
            f.write(content)
            logging.debug("EDITED FILE: %s" % path)

    def rm_file(self, path=None):
        if path is None:
            try:
                path = self.random_file()
            except IndexError: # no files
                return
        assert path.startswith(self.root)
        os.unlink(path)
        logging.debug("REMOVED FILE: %s" % path)

    def add_dir(self, path=None):
        if path is None:
            path = os.path.join(self.random_directory(True),
                                randstring(10))
        assert path.startswith(self.root)
        os.mkdir(path)
        logging.debug("CREATED DIRECTORY: %s" % path)
        
    def rm_dir(self, path=None):
        if path is None:
            try:
                path = self.random_directory(include_root=False)
            except IndexError: # no directories
                return
        assert path.startswith(self.root)
        if os.path.islink(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
        logging.debug("REMOVED DIRECTORY: %s" % path)

    def add_symlink(self, path=None, target=None):
        if path is None:
            path = os.path.join(self.random_directory(True),
                                randstring(10))
        if target is None:
            try:
                target = random.choice([self.random_file, self.random_directory])()
            except IndexError:
                return
        assert path.startswith(self.root)
        os.symlink(target, path)
        logging.debug("CREATED DIRECTORY: %s" % path)
        


class TestBackup(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tardisd-randomtesting")
        self.source = os.path.join(self.root, "source")
        os.mkdir(self.source)
        self.sourceTree = DirectoryTree(self.source)
        self.backups = os.path.join(self.root, "backups")
        os.mkdir(self.backups)

    def tearDown(self):
        #shutil.rmtree(self.root)
        pass

    def test_1(self):
        """This creates incremental backups of a directory tree by
        inserting random modifications and then creating a new backup a hundred times.
        It checks after each backup that the data is the same
        using the checksum function"""
        for i in range(10):
            # Make some changes to the data files
            self.sourceTree.make_random_changes(100)
            # get a checksum of the tree
            sum = self.sourceTree.checksum()
            logging.debug("data checmsum: %s" % sum)
            # Make a backup
            bkp = BackupChain("Test1", self.source, self.backups)
            b = bkp.make_backup()
            # make sure the source hasn't been modified
            self.assertEqual( self.sourceTree.checksum(), sum )
            # make sure that the cheksum s correct for this backup AND the old ones
            self.assertEqual(checksum(b.path, "source"), sum)
            # because rsync don't copy files that are < one second appart, 
            # we have to wait to make sure that the changes get detected.
            # (This shouldn't really be a problem in real application because no one
            # makes a backups every seconds or less...)
            sleep(1) 

    def test_2(self):
        """This test is a little bit different. It waits until all the iterative
        backups are done and verify that they all have the right checksum.
        So this checks that later backup didn't change previous ones."""
        try:
            checksums = []
            bkps = BackupChain("Test2", self.source, self.backups)
            for i in range(10):
                # Make some changes to the data files
                self.sourceTree.make_random_changes(100)
                # get a checksum of the tree
                sum = self.sourceTree.checksum()
                # Make a backup
                bkp = bkps.make_backup()
                # make sure the source hasn't been modified
                self.assertEqual( self.sourceTree.checksum(), sum )
                checksums += [sum]
                # because rsync don't copy files that are < one second appart, 
                # we have to wait to make sure that the changes get detected.
                # (This shouldn't really be a problem in real application because no one
                # makes a backups every seconds or less...)
                sleep(1) 
            for b,s in zip(bkps.history, checksums):
                self.assertEqual(checksum(b.path, "source"), s)
        except AssertionError: # raised by TestCase.fail, called by all asserts
            raise


if __name__ == '__main__':

    logging.basicConfig(level=logging.WARN)

    SEED = int(os.environ.get('SEED', random.randint(0, sys.maxint)))
    random.seed(SEED)
    print "SEED:", SEED
    unittest.main()


if __name__ == "__main__":
    tmp_backup_location = tempfile.mkdtemp()
    try:
        # Overriding the backup location for test purposes
        tardis.BKP_LOCATION = tmp_backup_location
        for i in range(1000):
            test_Backup()
        test_incremental_backups(1)
    finally:
        shutil.rmtree(tmp_backup_location)
