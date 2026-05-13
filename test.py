#!/usr/bin/env python3
import os
import subprocess
import threading
import time
import tempfile
import shutil
import signal
import sys

# -------- CONFIG --------
FUSE_BINARY = "fsx492"          # your compiled FS
FUSE_ARGS = ["-f", "-d", "-s"]  # run single threaded debug mode
MOUNT_TIMEOUT = 10              # seconds
# ------------------------


##############################################################################
# BEGIN TEST DEFINITIONS
##############################################################################

# define tests below by creating functions that are prefixed with "test_"


def test_basic(mountpoint):

    # TEST: directory listing

    print(f"[test] list {mountpoint}")
    entries = os.listdir(mountpoint)
    print(entries)
    assert "hello.txt" in entries, "readdir missing file"

    # TEST: file existence
    path = os.path.join(mountpoint, "hello.txt")
    print(f"[test] file existence: {path}")
    assert os.path.exists(path), "file missing"

    # TEST: read
    print(f"[test] read {path}")
    with open(path, "r") as f:
        data = f.read()
    assert "hello" in data, "unexpected file content"

    # TEST: partial read
    print(f"[test] partial read {path}")
    with open(path, "r") as f:
        f.seek(6)
        data = f.read()
    assert "world" in data, "partial read failed"

    # TEST: out of bounds read
    print(f"[test] out of bounds read {path}")
    with open(path, "r") as f:
        f.seek(30)
        data = f.read()
    assert len(data) == 0, "out of bounds read should return nothing"

    # TEST: stat
    print(f"[test] stat {path}")
    st = os.stat(path)
    assert st.st_size == len("hello world!\n"), "invalid file size"

    print("[test] passed basic")


def test_large_file(mountpoint):

    # TEST: large file copy
    src = "./data/gospels.txt"
    assert os.path.exists(src), "src not found: {}".format(src)

    dst = f"{mountpoint}/{os.path.basename(src)}"
    shutil.copy(src, dst)
    assert os.path.exists(dst), "copy failed: {} does not exist".format(dst)

    with open(src, 'rb') as f:
        srcdata = f.read()

    with open(dst, 'rb') as f:
        dstdata = f.read()

    assert len(srcdata) == len(dstdata), \
        "length check failed: {} (src) != {} (dst)".format(
            len(srcdata), len(dstdata))

    diff = -1
    for i in range(len(srcdata)):
        if srcdata[i] != dstdata[i]:
            diff = i
            break

    assert diff < 0, "data different @ {}:\nsrc: {}\ndst: {}".format(
        diff, srcdata[diff:diff+10], dstdata[diff:diff+10])

    print("[test] passed large file")

def test_nested_ops(mountpoint):
    # Create nested paths
    folder = os.path.join(mountpoint, "projects")
    item = os.path.join(folder, "notes.txt")

    print("[test] creating nested directory")
    os.mkdir(folder)

    print("[test] creating file in nested directory")
    with open(item, "w") as handle:
        handle.write("filesystem test data")

    assert os.path.isfile(item), "nested file creation failed"

    with open(item, "r") as handle:
        contents = handle.read()

    assert contents == "filesystem test data", "nested file contents mismatch"

    print("[test] deleting nested file")
    os.unlink(item)
    assert not os.path.exists(item), "nested file delete failed"

    print("[test] deleting nested directory")
    os.rmdir(folder)
    assert not os.path.exists(folder), "nested directory delete failed"

    print("[test] nested operations passed")


def test_directory_stress(mountpoint):
    # Parent directory for stress test
    parent = os.path.join(mountpoint, "bulkdirs")
    os.mkdir(parent)

    created = []

    print("[test] creating many directories")
    for idx in range(45):
        dirname = f"entry_{idx}"
        full = os.path.join(parent, dirname)
        os.mkdir(full)
        created.append(full)

    listing = os.listdir(parent)
    assert len(listing) == 45, "directory count mismatch"

    print("[test] removing many directories")
    for path in created:
        os.rmdir(path)

    remaining = os.listdir(parent)
    assert len(remaining) == 0, "directories were not fully removed"

    os.rmdir(parent)

    print("[test] directory stress passed")


def test_replace_contents(mountpoint):
    # Test overwrite behavior
    target = os.path.join(mountpoint, "replace_me.txt")

    with open(target, "w") as handle:
        handle.write("123456789")

    with open(target, "w") as handle:
        handle.write("abc")

    with open(target, "r") as handle:
        result = handle.read()

    assert result == "abc", f"truncate overwrite failed: {result}"

    metadata = os.stat(target)
    assert metadata.st_size == 3, "file size incorrect after overwrite"

    print("[test] overwrite passed")


def test_append_behavior(mountpoint):
    # Test append mode
    target = os.path.join(mountpoint, "journal.txt")

    with open(target, "w") as handle:
        handle.write("first")

    with open(target, "a") as handle:
        handle.write("second")

    with open(target, "r") as handle:
        combined = handle.read()

    assert combined == "firstsecond", "append mode failed"

    print("[test] append behavior passed")


def test_link_tracking(mountpoint):
    # Test hard links
    source = os.path.join(mountpoint, "alpha.txt")
    alias = os.path.join(mountpoint, "beta.txt")

    with open(source, "w") as handle:
        handle.write("shared content")

    initial_links = os.stat(source).st_nlink
    assert initial_links == 1, "initial link count incorrect"

    os.link(source, alias)

    after_link = os.stat(alias).st_nlink
    assert after_link == 2, f"link count did not increment, got {after_link}"

    with open(alias, "r") as handle:
        copied = handle.read()

    assert copied == "shared content", "linked file data mismatch"

    os.remove(alias)

    final_links = os.stat(source).st_nlink
    assert final_links == 1, "link count did not decrement"

    print("[test] hard link tracking passed")


def test_timestamp_changes(mountpoint):
    # Test timestamp updates
    filename = os.path.join(mountpoint, "clocktest.txt")

    with open(filename, "w") as handle:
        handle.write("time data")

    before = os.stat(filename)

    time.sleep(1)

    with open(filename, "r") as handle:
        handle.read()

    after_read = os.stat(filename)
    assert after_read.st_atime >= before.st_atime, "access time unchanged"

    time.sleep(1)

    with open(filename, "w") as handle:
        handle.write("updated")

    after_write = os.stat(filename)
    assert after_write.st_mtime > after_read.st_mtime, "modification time unchanged"

    print("[test] timestamp updates passed")


def test_permission_changes(mountpoint):
    # Test chmod
    filename = os.path.join(mountpoint, "secure.txt")

    with open(filename, "w") as handle:
        handle.write("permissions")

    os.chmod(filename, 0o700)
    perms = os.stat(filename).st_mode & 0o777
    assert perms == 0o700, f"expected 700, got {oct(perms)}"

    os.chmod(filename, 0o644)
    perms = os.stat(filename).st_mode & 0o777
    assert perms == 0o644, f"expected 644, got {oct(perms)}"

    print("[test] permission changes passed")


def test_create_write_read(mountpoint):
    path = os.path.join(mountpoint, "newfile.txt")
    data = "CS492 filesystem test\n"

    print(f"[test] create/write/read {path}")
    with open(path, "w") as f:
        f.write(data)

    assert os.path.exists(path), "created file does not exist"

    with open(path, "r") as f:
        read_back = f.read()

    assert read_back == data, "read data does not match written data"

    st = os.stat(path)
    assert st.st_size == len(data), "created file has wrong size"

    print("[test] passed create_write_read")


def test_overwrite_partial(mountpoint):
    path = os.path.join(mountpoint, "overwrite.txt")

    print(f"[test] partial overwrite {path}")
    with open(path, "w") as f:
        f.write("abcdefghij")

    with open(path, "r+") as f:
        f.seek(3)
        f.write("XYZ")

    with open(path, "r") as f:
        data = f.read()

    assert data == "abcXYZghij", f"partial overwrite failed: {data}"

    print("[test] passed overwrite_partial")


def test_unlink_file(mountpoint):
    path = os.path.join(mountpoint, "delete_me.txt")

    print(f"[test] unlink {path}")
    with open(path, "w") as f:
        f.write("delete me")

    assert os.path.exists(path), "file was not created"

    os.unlink(path)

    assert not os.path.exists(path), "file still exists after unlink"

    print("[test] passed unlink_file")


def test_mkdir_rmdir(mountpoint):
    dirpath = os.path.join(mountpoint, "newdir")

    print(f"[test] mkdir/rmdir {dirpath}")
    os.mkdir(dirpath)

    assert os.path.exists(dirpath), "directory was not created"
    assert os.path.isdir(dirpath), "created path is not a directory"

    entries = os.listdir(mountpoint)
    assert "newdir" in entries, "new directory missing from parent listing"

    os.rmdir(dirpath)

    assert not os.path.exists(dirpath), "directory still exists after rmdir"

    print("[test] passed mkdir_rmdir")


def test_nested_create_read(mountpoint):
    dirpath = os.path.join(mountpoint, "nested")
    filepath = os.path.join(dirpath, "inside.txt")
    data = "inside nested directory\n"

    print(f"[test] nested create/read {filepath}")
    os.mkdir(dirpath)

    with open(filepath, "w") as f:
        f.write(data)

    assert os.path.exists(filepath), "nested file was not created"

    with open(filepath, "r") as f:
        read_back = f.read()

    assert read_back == data, "nested file content mismatch"

    entries = os.listdir(dirpath)
    assert "inside.txt" in entries, "nested file missing from directory listing"

    print("[test] passed nested_create_read")


def test_rmdir_not_empty(mountpoint):
    dirpath = os.path.join(mountpoint, "notempty")
    filepath = os.path.join(dirpath, "child.txt")

    print(f"[test] rmdir non-empty directory {dirpath}")
    os.mkdir(dirpath)

    with open(filepath, "w") as f:
        f.write("child")

    failed = False
    try:
        os.rmdir(dirpath)
    except OSError:
        failed = True

    assert failed, "rmdir should fail on non-empty directory"
    assert os.path.exists(filepath), "child file disappeared after failed rmdir"

    print("[test] passed rmdir_not_empty")


def test_rename_file(mountpoint):
    oldpath = os.path.join(mountpoint, "oldname.txt")
    newpath = os.path.join(mountpoint, "newname.txt")
    data = "rename data\n"

    print(f"[test] rename {oldpath} -> {newpath}")
    with open(oldpath, "w") as f:
        f.write(data)

    os.rename(oldpath, newpath)

    assert not os.path.exists(oldpath), "old path still exists after rename"
    assert os.path.exists(newpath), "new path does not exist after rename"

    with open(newpath, "r") as f:
        read_back = f.read()

    assert read_back == data, "renamed file content mismatch"

    print("[test] passed rename_file")


def test_hard_link(mountpoint):
    oldpath = os.path.join(mountpoint, "original.txt")
    newpath = os.path.join(mountpoint, "linked.txt")
    data = "hard link data\n"

    print(f"[test] hard link {oldpath} -> {newpath}")
    with open(oldpath, "w") as f:
        f.write(data)

    os.link(oldpath, newpath)

    assert os.path.exists(oldpath), "original file missing after link"
    assert os.path.exists(newpath), "linked file missing"

    with open(newpath, "r") as f:
        read_back = f.read()

    assert read_back == data, "linked file content mismatch"

    with open(newpath, "w") as f:
        f.write("changed through link\n")

    with open(oldpath, "r") as f:
        changed = f.read()

    assert changed == "changed through link\n", "hard link does not refer to same inode"

    os.unlink(newpath)
    assert os.path.exists(oldpath), "unlinking hard link removed original"

    print("[test] passed hard_link")


def test_truncate_smaller(mountpoint):
    path = os.path.join(mountpoint, "truncate_small.txt")

    print(f"[test] truncate smaller {path}")
    with open(path, "w") as f:
        f.write("0123456789")

    os.truncate(path, 4)

    st = os.stat(path)
    assert st.st_size == 4, f"wrong size after truncate smaller: {st.st_size}"

    with open(path, "r") as f:
        data = f.read()

    assert data == "0123", f"wrong data after truncate smaller: {data}"

    print("[test] passed truncate_smaller")


def test_truncate_larger(mountpoint):
    path = os.path.join(mountpoint, "truncate_large.txt")

    print(f"[test] truncate larger {path}")
    with open(path, "w") as f:
        f.write("abc")

    os.truncate(path, 10)

    st = os.stat(path)
    assert st.st_size == 10, f"wrong size after truncate larger: {st.st_size}"

    with open(path, "rb") as f:
        data = f.read()

    assert data[:3] == b"abc", "original data changed after truncate larger"
    assert data[3:] == b"\x00" * 7, "extended bytes should read as zeroes"

    print("[test] passed truncate_larger")


def test_chmod(mountpoint):
    path = os.path.join(mountpoint, "chmod_file.txt")

    print(f"[test] chmod {path}")
    with open(path, "w") as f:
        f.write("chmod")

    os.chmod(path, 0o600)

    st = os.stat(path)
    assert (st.st_mode & 0o777) == 0o600, oct(st.st_mode & 0o777)

    os.chmod(path, 0o644)

    st = os.stat(path)
    assert (st.st_mode & 0o777) == 0o644, oct(st.st_mode & 0o777)

    print("[test] passed chmod")


def test_utimens(mountpoint):
    path = os.path.join(mountpoint, "time_file.txt")

    print(f"[test] utimens {path}")
    with open(path, "w") as f:
        f.write("time")

    atime = 1000000000
    mtime = 1000000050
    os.utime(path, (atime, mtime))

    st = os.stat(path)

    assert int(st.st_atime) == atime, f"bad atime: {st.st_atime}"
    assert int(st.st_mtime) == mtime, f"bad mtime: {st.st_mtime}"

    print("[test] passed utimens")


def test_statfs(mountpoint):
    print(f"[test] statvfs {mountpoint}")
    st = os.statvfs(mountpoint)

    assert st.f_bsize > 0, "bad block size"
    assert st.f_blocks > 0, "bad block count"
    assert st.f_files > 0, "bad inode count"
    assert st.f_namemax > 0, "bad max filename length"

    print("[test] passed statfs")


def test_error_cases(mountpoint):
    print("[test] basic error cases")

    missing = os.path.join(mountpoint, "does_not_exist.txt")
    failed = False
    try:
        open(missing, "r").close()
    except FileNotFoundError:
        failed = True
    assert failed, "opening missing file should fail"

    dirpath = os.path.join(mountpoint, "errordir")
    os.mkdir(dirpath)

    failed = False
    try:
        os.unlink(dirpath)
    except OSError:
        failed = True
    assert failed, "unlink on directory should fail"

    filepath = os.path.join(mountpoint, "regular.txt")
    with open(filepath, "w") as f:
        f.write("regular")

    failed = False
    try:
        os.rmdir(filepath)
    except OSError:
        failed = True
    assert failed, "rmdir on regular file should fail"

    print("[test] passed error_cases")



def test_hard_link_basic(mountpoint):
    oldpath = os.path.join(mountpoint, "original.txt")
    newpath = os.path.join(mountpoint, "linked.txt")
    data = "hard link data\n"

    print(f"[test] hard link basic {oldpath} -> {newpath}")

    with open(oldpath, "w") as f:
        f.write(data)

    os.link(oldpath, newpath)

    old_st = os.stat(oldpath)
    new_st = os.stat(newpath)

    assert old_st.st_nlink >= 2, f"original nlink should be at least 2, got {old_st.st_nlink}"
    assert new_st.st_nlink >= 2, f"linked nlink should be at least 2, got {new_st.st_nlink}"

    with open(newpath, "r") as f:
        read_back = f.read()

    assert read_back == data, "linked file content mismatch"

    os.unlink(newpath)
    assert os.path.exists(oldpath), "unlinking linked name removed original"

    with open(oldpath, "r") as f:
        read_back = f.read()

    assert read_back == data, "original content changed after unlinking hard link"

    print("[test] passed hard_link_basic")


##############################################################################
# END TEST DEFINITIONS
##############################################################################

TESTS = {
    k.removeprefix('test_'): v for k, v in globals().items() if k.startswith('test_')
}


def reset_mount(mountpoint, fs_name=FUSE_BINARY):
    """reset fuse filesystem mountpoint after failure"""
    result = subprocess.run(
        ['mount'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False)

    if fs_name in result.stdout:
        subprocess.run(
            ['fusermount', '-u', mountpoint],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False)

    try:
        shutil.rmtree(mountpoint)
    except Exception:
        pass

    os.makedirs(mountpoint, exist_ok=True)

def is_mounted(mountpoint, fs_name=None):
    mountpoint = os.path.abspath(mountpoint)

    try:
        with open("/proc/self/mounts", "r") as f:
            lines = [line.strip() for line in f.readlines()]

        for line in lines:
            parts = line.split()
            if len(parts) < 3:
                continue

            dev, mnt, fstype = parts[:3]

            if os.path.abspath(mnt) == mountpoint:
                if fs_name is None:
                    return True
                if fs_name in dev or fs_name in fstype:
                    return True
        return False
    except Exception:
        return False


def wait_for_mount(mountpoint, timeout=MOUNT_TIMEOUT):
    """Wait until mountpoint is ready by probing it."""
    start = time.time()
    while time.time() - start < timeout:
        if is_mounted(mountpoint, fs_name="fsx492"):
            return True
        time.sleep(0.1)
    return False


def run_filesystem(mountpoint, ready_event, stop_event, logfile="fsx492.log"):
    """Run the FUSE filesystem."""
    cmd = ['stdbuf', '-oL', '-eL'] + [f"./{FUSE_BINARY}"] + FUSE_ARGS + ["--img", "data/test.img", mountpoint]

    # unmount file system if needed first
    reset_mount(mountpoint)

    log = open(logfile, 'w')
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Wait until mount is ready
    if wait_for_mount(mountpoint):
        print("[fs] mounted")
        ready_event.set()
    else:
        print("[fs] mount timeout")
        proc.terminate()
        return

    # Keep process alive until stop_event
    while not stop_event.is_set():
        if proc.poll() is not None:
            print("[fs] process exited early!")
            return
        time.sleep(0.2)

    log.close()
    print("[fs] shutting down...")
    proc.send_signal(signal.SIGINT)

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_tests(test, mountpoint, ready_event, stop_event):
    """Run filesystem tests."""
    ready_event.wait()

    print(f"[test] starting test: {test}")

    try:
        TESTS[test](mountpoint)
    except AssertionError as e:
        print(f"[test] FAILED: {e}")
    finally:
        stop_event.set()


if __name__ == "__main__":
    DEFAULT_MOUNTPOINT = './testfs'
    DEFAULT_IMAGE = 'data/test.img'
    import argparse
    parser = argparse.ArgumentParser('test.py',
        description="test script for fsx492")
    parser.add_argument('test', type=str, default='basic',
        help=f"options: {','.join(TESTS.keys())}")
    parser.add_argument('--mountpoint', type=str, default=DEFAULT_MOUNTPOINT,
        help=f"the path to mount at (default {DEFAULT_MOUNTPOINT})")
    parser.add_argument('--img', type=str, default='data/test.img',
        help=("the path to the image file, which will be restored from backup "
            f"(default: {DEFAULT_IMAGE})"))

    args = parser.parse_args()

    mountpoint = args.mountpoint
    assert args.test in TESTS, "test not found: {}".format(args.test)
    assert callable(TESTS[args.test]), "not callable: {}".format(args.test)

    imgpath = args.img
    assert os.path.exists(imgpath), "file not found: {}".format(imgpath)
    imgbkp = f"{imgpath}.bkp"
    assert os.path.exists(imgbkp), "could not find backup: {}".format(imgbkp)

    print(f"[main] cwd: {os.getcwd()}")
    print(f"[main] mountpoint: {mountpoint}")
    print(f"[main] restoring {imgpath} from {imgbkp}")
    shutil.copy(imgbkp, imgpath)

    ready_event = threading.Event()
    stop_event = threading.Event()

    fs_thread = threading.Thread(
        target=run_filesystem,
        args=(mountpoint, ready_event, stop_event),
        daemon=True
    )

    test_thread = threading.Thread(
        target=run_tests,
        args=(args.test, mountpoint, ready_event, stop_event),
        daemon=True
    )

    fs_thread.start()
    test_thread.start()

    test_thread.join()
    stop_event.set()
    fs_thread.join()

    # Try to unmount (Linux)
    print("[main] unmounting...")
    subprocess.run(["fusermount", "-u", mountpoint],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)

    shutil.rmtree(mountpoint)
    print("[main] done")


