#include <stdint.h>
#include <string.h>

#define MAX_HANDLES 8
#define BUFFER_SIZE 256

static uint8_t buffers[MAX_HANDLES][BUFFER_SIZE];
static int connected[MAX_HANDLES];

static int valid_handle(int handle) {
    return handle > 0 && handle <= MAX_HANDLES;
}

static int valid_range(int handle, int index, int size) {
    return valid_handle(handle) && index >= 0 && size >= 0 && index + size <= BUFFER_SIZE;
}

int unidriver_read_bytes(int handle, int index, uint8_t *out, int size) {
    if (!valid_range(handle, index, size)) {
        return -1;
    }
    memcpy(out, buffers[handle - 1] + index, (size_t)size);
    connected[handle - 1] = 1;
    return 0;
}

int unidriver_write_bytes(int handle, int index, const uint8_t *data, int size) {
    if (!valid_range(handle, index, size)) {
        return -1;
    }
    memcpy(buffers[handle - 1] + index, data, (size_t)size);
    connected[handle - 1] = 1;
    return 0;
}

int unidriver_read_bit(int handle, int byte_index, int bit_index, int *out) {
    if (!valid_range(handle, byte_index, 1) || bit_index < 0 || bit_index > 7) {
        return -1;
    }
    *out = (buffers[handle - 1][byte_index] >> bit_index) & 1;
    connected[handle - 1] = 1;
    return 0;
}

int unidriver_write_bit(int handle, int byte_index, int bit_index, int value) {
    if (!valid_range(handle, byte_index, 1) || bit_index < 0 || bit_index > 7) {
        return -1;
    }
    if (value) {
        buffers[handle - 1][byte_index] |= (uint8_t)(1u << bit_index);
    } else {
        buffers[handle - 1][byte_index] &= (uint8_t)~(1u << bit_index);
    }
    connected[handle - 1] = 1;
    return 0;
}

int unidriver_tick(void) {
    return 0;
}

int unidriver_is_connected(int handle) {
    return valid_handle(handle) && connected[handle - 1];
}
