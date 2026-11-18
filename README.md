# FSX492 — User-Space File System in C

A custom user-space file system implemented in C using FUSE (Filesystem in Userspace). Built for CS 492 at Stevens Institute of Technology, this project implements core file system functionality over a simulated block device, including file and directory management, inode tracking, permissions, and link handling.

Rather than relying on an existing file system, FSX492 manages its own on-disk structures and translates standard Linux file operations into reads and writes against a disk image.

## Features

### File System Operations

- **File I/O:** Create, open, read, write, truncate, and delete files.
- **Directories:** Create, remove, list, and navigate directories, including nested directory structures.
- **Inode Management:** Track file metadata, block references, ownership, timestamps, and hard-link counts.
- **Block Storage:** Read and write through a simulated block device, with support for files and directories spanning multiple blocks.
- **Hard Links:** Support multiple directory entries referencing the same inode, with appropriate link-count management.
- **Permissions:** Support file permission changes and access checks.
- **Symbolic Links:** Implement symbolic link creation and resolution, including links to files and directories.

Access control and symbolic links were implemented as additional features beyond the core assignment requirements.

## Architecture

The file system is divided into three main components:

| Component | Description |
|---|---|
| `main.c` | Initializes the block device, processes command-line options, and mounts the file system through FUSE. |
| `src/fsx492.c` | Implements file system operations, inode management, directory handling, and FUSE callbacks. |
| `src/blkdev.c` | Provides the simulated block device interface for reading, writing, and managing disk blocks. |

### On-Disk Structure

FSX492 uses a disk image with several structures:

- **Superblock:** Stores file system configuration and metadata.
- **Inode bitmap:** Tracks allocated and available inodes.
- **Block bitmap:** Tracks allocated and available disk blocks.
- **Inode table:** Stores file metadata and pointers to data blocks.
- **Data blocks:** Store file contents and directory entries.

Each inode records information such as file size, permissions, ownership, timestamps, link count, and block pointers. The layout includes direct and indirect block references.

File system operations are handled through FUSE callbacks, allowing standard Linux commands to interact with the custom file system.

## Building and Running

### Requirements

- Linux environment with FUSE 3 support
- GCC
- Make
- `pkg-config`
- Python 3 for testing

On Ubuntu or Debian, the build dependencies can be installed with:

```bash
sudo apt install build-essential pkg-config libfuse3-dev fuse3 python3
```

### Build

Clone the repository and compile the file system:

```bash
git clone https://github.com/RMLaumeyer/CS492-FS.git
cd CS492-FS
make
```

This builds the `fsx492` executable.

### Mount the File System

Reset the test disk image and prepare the mount directory:

```bash
make reset
```

Start the file system:

```bash
make mount
```

The file system mounts at `./testfs` using `data/test.img`.

The provided Makefile runs FUSE in single-threaded debug mode. Keep that process running while interacting with the mounted directory from another terminal.

You can then use standard Linux commands:

```bash
ls testfs
mkdir testfs/example
echo "Hello, FUSE!" > testfs/example/hello.txt
cat testfs/example/hello.txt
```

Unmount the file system when finished:

```bash
fusermount -u ./testfs
```

## Testing

A Python test suite (`test.py`) exercises file system functionality through standard file and directory operations.

Test coverage includes:

- Creating and removing files and directories.
- Working with nested directories and directories spanning multiple blocks.
- File reads, writes, overwrites, appends, and truncation.
- Hard-link creation and link-count tracking.
- Permission changes and access-related behavior.
- File metadata and timestamp updates.
- Error handling for invalid file system operations.

To run an individual test:

```bash
python3 test.py basic
```

The test runner restores the disk image from its backup, mounts the file system, executes the selected test, and performs cleanup.

Additional test names can be found in `test.py`.

## Technical Challenges

Several parts of the implementation required careful handling of file system state and POSIX behavior.

**Block and inode management:** File operations must maintain consistency between allocated blocks, inode metadata, and directory entries. Larger files and directories also require handling data beyond a single block.

**Hard links and deletion:** Removing a directory entry does not necessarily mean deleting its underlying file data. Link counts must be maintained so that shared inodes remain valid until their references are removed.

**File I/O behavior:** Writes, appends, overwrites, and truncation must update both file contents and metadata correctly, including operations that cross block boundaries.

**Permissions and symbolic links:** Extending the file system with access control and symbolic links required additional handling of file metadata, path resolution, and error conditions.

## Repository Structure

```text
CS492-FS/
├── data/             # Test disk images and sample data
├── include/          # Header files and data structures
├── src/
│   ├── blkdev.c      # Block device implementation
│   └── fsx492.c      # File system implementation
├── utils/            # Supporting utilities
├── main.c            # FUSE entry point
├── Makefile          # Build and mount commands
├── test.py           # Python test suite
├── screenshots.pdf   # Project screenshots
└── README.md
```

## Technologies

C, Linux, FUSE 3, GCC, Make, Python, POSIX File System APIs

## Contributors

Developed as a group project for CS 492 at Stevens Institute of Technology.

- Robert Laumeyer
- Louis Lazzarini
- James McDermott

## References

- [libfuse documentation](https://libfuse.github.io/doxygen/)
- [Linux manual pages](https://man7.org/linux/man-pages/)
- [POSIX specifications](https://pubs.opengroup.org/onlinepubs/9799919799/)
