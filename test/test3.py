import zipfile
from zipfile import ZipFile, ZipInfo
import shutil
import os
def _extract_member(self, member, targetpath, pwd):
    """Extract the ZipInfo object 'member' to a physical
       file on the path targetpath.
    """
    if not isinstance(member, ZipInfo):
        member = self.getinfo(member)

    if os.path.sep == '/':
        arcname = member.filename.replace('\\', os.path.sep)
    else:
        arcname = member.filename.replace('/', os.path.sep)

    if os.path.altsep:
        arcname = arcname.replace(os.path.altsep, os.path.sep)
    # interpret absolute pathname as relative, remove drive letter or
    # UNC path, redundant separators, "." and ".." components.
    arcname = os.path.splitdrive(arcname)[1]
    invalid_path_parts = ('', os.path.curdir, os.path.pardir)
    arcname = os.path.sep.join(x for x in arcname.split(os.path.sep)
                               if x not in invalid_path_parts)
    if os.path.sep == '\\':
        # filter illegal characters on Windows
        arcname = self._sanitize_windows_name(arcname, os.path.sep)

    targetpath = os.path.join(targetpath, arcname)
    targetpath = os.path.normpath(targetpath)

    # Create all upper directories if necessary.
    upperdirs = os.path.dirname(targetpath)
    if upperdirs and not os.path.exists(upperdirs):
        os.makedirs(upperdirs)

    if member.is_dir():
        if not os.path.isdir(targetpath):
            os.mkdir(targetpath)
        return targetpath

    with self.open(member, pwd=pwd) as source, \
            open(targetpath, "wb") as target:
        shutil.copyfileobj(source, target)

    return targetpath
ZipFile._extract_member = _extract_member

if __name__ == '__main__':

    with zipfile.ZipFile('jsp-demo2.zip', 'r') as zip_ref:
        zip_ref.extractall('jsp-demo')