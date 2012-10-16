import os, sys
import shutil
import subprocess
import logging

def rsync(source, destination, excludes=[], dry=False, logfile=None):
    command = ["rsync","--archive", "--delete", "--verbose"]
    if dry:
        command += ["--dry-run"]
    for e in excludes:
        command += ["--exclude", e]
    command += [source, destination]
    logging.info("Starting rsync: %s" % command)
    if logfile is not None:
        with open(logfile,"a") as logf:
            logging.info("rsync is logging to %s" % logfile)
            status = subprocess.call(command, stdout=logf, stderr=logf)
    elif dry:
        status = subprocess.call(command, stdout=sys.stdout, stderr=sys.stderr)
    else:
        status = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if status == 23:
        logging.warn("Partial transfer due to error (rsync error 23)")
        return
    if status == 24:
        logging.warn("Partial transfer due to vanished source files (rsync error 24)")
        return
    assert status == 0, "Rsync exited with non zero status: %d" % status

def copytree(src, dst):
    """A special version of copytree, from the shutil module, 
    where hardlink are used instead of actually copying the files."""
    names = os.listdir(src)
    os.makedirs(dst)
    # Copy metadata:
    shutil.copystat(src, dst)
    # copystat doesn't care for the owner/group so I wrote a custom function
    copyown(src,dst)
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
    if errors:
        print errors
        assert False

def copyown(src,dst):
    s = os.stat(src)
    uid = s.st_uid
    gid = s.st_gid
    os.chown(dst,uid,gid)
