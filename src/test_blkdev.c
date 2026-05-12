#include <stdio.h>
#include <string.h>
#include <assert.h>

#include "blkdev.h"

int main(void)
{
    struct blkdev dev;

    printf("Testing blkdev_init...\n");

    int ret = blkdev_init(&dev, "data/test.img");
    printf("blkdev_init returned: %d\n", ret);
    assert(ret == BLKDEV_SUCCESS);

    printf("Testing size...\n");

    int size = dev.ops->size(&dev);
    printf("size returned: %d blocks\n", size);
    assert(size == 100);

    printf("Testing write/read...\n");

    char write_buf[BLKDEV_BLKSZ];
    char read_buf[BLKDEV_BLKSZ];

    memset(write_buf, 0, BLKDEV_BLKSZ);
    memset(read_buf, 0, BLKDEV_BLKSZ);

    strcpy(write_buf, "hello blkdev");

    ret = dev.ops->write(&dev, 5, 1, write_buf);
    printf("write returned: %d\n", ret);
    assert(ret == BLKDEV_SUCCESS);

    ret = dev.ops->read(&dev, 5, 1, read_buf);
    printf("read returned: %d\n", ret);
    assert(ret == BLKDEV_SUCCESS);

    printf("read back: %s\n", read_buf);
    assert(strcmp(read_buf, "hello blkdev") == 0);

    printf("Testing invalid read...\n");

    ret = dev.ops->read(&dev, 9999, 1, read_buf);
    printf("bad read returned: %d\n", ret);
    assert(ret != BLKDEV_SUCCESS);

    printf("Testing invalid write...\n");

    ret = dev.ops->write(&dev, 9999, 1, write_buf);
    printf("bad write returned: %d\n", ret);
    assert(ret != BLKDEV_SUCCESS);

    printf("Testing close...\n");

    dev.ops->close(&dev);

    printf("All blkdev tests passed!\n");

    return 0;
}