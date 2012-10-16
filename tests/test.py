import os
print os.getcwd()
from tardisd.backup import Backup, BackupChain
import random
import unittest
import datetime
import tempfile
import shutil
import string
from time import sleep
from subprocess import Popen, PIPE
from commands import getstatusoutput as run
import logging
logging.basicConfig(level=logging.DEBUG)


def randdatetime():
    return datetime.datetime.fromtimestamp(random.randrange(2147483648))

def checksum(root, path):
    """Compute a checksum for a file hierarchy"""
    tar = Popen(["tar", "-cf", "-", path], cwd=root, stdout=PIPE, stderr=PIPE)
    md5sum = Popen("md5sum", stdin = tar.stdout, stdout=PIPE)
    assert tar.wait() == 0, "tar error: %s" % tar.stderr.read()
    assert md5sum.wait() == 0, "md5um error"
    return md5sum.stdout.read().split()[0]

def randstring(size):
    ltrs = [random.choice(string.ascii_letters) for i in range(size)]
    return ''.join(ltrs)

# def test_incremental_backups(niterations=10):
#     # Create testing environment
#     testing_location = tempfile.mkdtemp()
#     try:
#         bkp_location = os.path.join(testing_location, "backups")
#         os.mkdir(bkp_location)
#         src_location = os.path.join(testing_location, "source")
#         os.mkdir(src_location)
#         src_data_root = os.path.join(src_location, "root")
#         os.mkdir(src_data_root)
#         bkps = BackupChain("Test", src_location, bkp_location)
#         for i in range(niterations):
#             # Make some changes to the data files
#             for j in range(100):
#                 action = random.choice(["ADD_FILE", 
#                                         "ADD_DIR",
#                                         "CHANGE_FILE", 
#                                         "RM_FILE", 
#                                         "RM_DIR"])
#                 if action == "ADD_FILE":
#                     d = get_random_dir(src_data_root, True)
#                     path = os.path.join(src_data_root, d, randstring(10) + ".txt")
#                     with open(path, "w") as f:
#                         f.write(randstring(100))
#                     logging.debug("CREATED FILE: %s" % path)
#                 elif action == "ADD_DIR":
#                     path = os.path.join(src_data_root,
#                                         get_random_dir(src_data_root, True),
#                                         randstring(10))
#                     os.mkdir(path)
#                     logging.debug("CREATED DIRECTORY: %s" % path)
#                 elif action == "CHANGE_FILE":
#                     try:
#                         path = os.path.join(src_data_root,
#                                             get_random_file(src_data_root))
#                         with open(path, random.choice(['w', 'a'])) as f:
#                             f.write(randstring(100))
#                         logging.debug("EDITED FILE: %s" % path)
#                     except IndexError: # no files
#                         pass                    
#                 elif action == "RM_FILE":
#                     try:
#                         path = get_random_file(src_data_root)
#                         os.unlink(path)
#                         logging.debug("REMOVED FILE: %s" % path)
#                     except IndexError: # no files
#                         pass
#                 elif action == "RM_DIR":
#                     try:
#                         path = get_random_dir(src_data_root, False)
#                         shutil.rmtree(path)
#                         logging.debug("REMOVED DIRECTORY: %s" % path)
#                     except IndexError: # no directories
#                         pass
                        
#             # get a checksum of the tree
#             cs = checksum(src_location, "root")
#             logging.debug("data checmsum: %s" % cs)
#             # Make an incremental backup
#             bkps.make_backup()
#             # make sure that the cheksum s correct for this backup AND the old ones
            
#     finally:
#         pass
#         #shutil.rmtree(testing_location)

class TestBackup(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_when(self):
        before = datetime.datetime.now()
        b = Backup(self.root)
        after = datetime.datetime.now()
        print before, b.when, after
        self.assertTrue(before < b.when)
        self.assertTrue(b.when < after)

    def test_iscomplete(self):
        d = randdatetime()
        b = Backup(self.root, when=d)
        self.assertFalse(b.iscomplete())
        os.mkdir(b.path)
        self.assertTrue(b.iscomplete())
        del b
        
        b = Backup(self.root, when=d)
        self.assertTrue(b.iscomplete())
        os.rmdir(b.path)
        self.assertFalse(b.iscomplete())
        del b


class TrucateFileTestCase(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tardisd-testing")
        self.source = os.path.join(self.root, "source")
        os.mkdir(self.source)
        self.backups = os.path.join(self.root, "backups")
        os.mkdir(self.backups)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_backup_truncated_file(self):
        """Subtile case where a file is truncated but keep the same size."""
        fpath = os.path.join(self.source, "file.txt")
        with open(fpath,"a") as f:
            f.write("*"*100 + "\n")
        bkps = BackupChain("Test1", self.source, self.backups)
        b = bkps.make_backup()
        self.assertEqual(checksum(b.path, "source"), checksum(self.root, "source"))

        with open(fpath,"a") as f:
            f.write("#"*100 + "\n")
        b = bkps.make_backup()
        self.assertEqual(checksum(b.path, "source"), checksum(self.root, "source"))


class DeleteFileTestCase(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tardisd-testing")
        self.source = os.path.join(self.root, "source")
        os.mkdir(self.source)
        self.backups = os.path.join(self.root, "backups")
        os.mkdir(self.backups)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_remove_deleted_file(self):
        """Check that rsyn does really delete files that have been
        deleted from the source directory."""
        fpath = os.path.join(self.source, "file.txt")
        with open(fpath,"a") as f:
            f.write("*"*100 + "\n")
        bkps = BackupChain("Test1", self.source, self.backups)
        b = bkps.make_backup()
        self.assertEqual(checksum(b.path, "source"), checksum(self.root, "source"))
        os.unlink(fpath)
        b = bkps.make_backup()
        self.assertEqual(checksum(b.path, "source"), checksum(self.root, "source"))


if __name__ == '__main__':
    unittest.main()
