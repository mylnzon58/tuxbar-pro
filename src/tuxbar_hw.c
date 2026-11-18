/*
 * src/tuxbar_hw.c — Low-level Linux DRM/KMS + evdev multitouch + uinput bridge
 * Project: TuxBar Pro (mylnzon58)
 *
 * Compiles to libtuxbar_hw.so on Linux (Ubuntu 24.04 LTS / kernel linux-t2).
 */

#ifdef __linux__
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

typedef struct {
    int drm_fd;
    uint32_t conn_id;
    uint32_t crtc_id;
    uint32_t fb_id;
    uint32_t handle;
    uint32_t pitch;
    uint64_t size;
    uint32_t width;
    uint32_t height;
    uint8_t *map;
    drmModeModeInfo mode;

    int uinput_fd;
    int touch_fd;
    int touch_max_x;
    int touch_max_y;
    int touch_swapped_xy;
    int cur_raw_x;
    int cur_raw_y;
    int touching;
} TuxBarHW;

static int open_touch_device(TuxBarHW *hw) {
    for (int i = 0; i < 32; i++) {
        char path[64];
        snprintf(path, sizeof(path), "/dev/input/event%d", i);
        int fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) continue;

        char name[128] = {0};
        ioctl(fd, EVIOCGNAME(sizeof(name)), name);
        if (strcasestr(name, "TouchBar") || strcasestr(name, "Touch Bar") ||
            strcasestr(name, "iBridge") || strcasestr(name, "DFR")) {
            struct input_absinfo abs_x = {0}, abs_y = {0};
            ioctl(fd, EVIOCGABS(ABS_MT_POSITION_X), &abs_x);
            ioctl(fd, EVIOCGABS(ABS_MT_POSITION_Y), &abs_y);
            hw->touch_fd = fd;
            hw->touch_max_x = (abs_x.maximum > 0) ? abs_x.maximum : 2170;
            hw->touch_max_y = (abs_y.maximum > 0) ? abs_y.maximum : 60;
            hw->touch_swapped_xy = (hw->touch_max_y > hw->touch_max_x) ? 1 : 0;
            return 0;
        }
        close(fd);
    }
    return -1;
}

static int open_uinput_device(TuxBarHW *hw) {
    int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return -1;

    ioctl(fd, UI_SET_EVBIT, EV_KEY);
    ioctl(fd, UI_SET_EVBIT, EV_SYN);
    for (int k = 1; k < 256; k++) {
        ioctl(fd, UI_SET_KEYBIT, k);
    }

    struct uinput_setup usetup;
    memset(&usetup, 0, sizeof(usetup));
    usetup.id.bustype = BUS_USB;
    usetup.id.vendor = 0x05ac;
    usetup.id.product = 0x8600;
    snprintf(usetup.name, UINPUT_MAX_NAME_SIZE, "TuxBar Pro Virtual Keyboard");

    if (ioctl(fd, UI_DEV_SETUP, &usetup) < 0 || ioctl(fd, UI_DEV_CREATE) < 0) {
        close(fd);
        return -1;
    }
    hw->uinput_fd = fd;
    return 0;
}

static void emit_key(int fd, uint16_t type, uint16_t code, int32_t val) {
    struct input_event ie;
    memset(&ie, 0, sizeof(ie));
    ie.type = type;
    ie.code = code;
    ie.value = val;
    (void)write(fd, &ie, sizeof(ie));
}

int tuxbar_hw_open(TuxBarHW *hw) {
    if (!hw) return -1;
    memset(hw, 0, sizeof(*hw));
    hw->drm_fd = -1;
    hw->uinput_fd = -1;
    hw->touch_fd = -1;

    for (int i = 0; i < 8; i++) {
        char path[64];
        snprintf(path, sizeof(path), "/dev/dri/card%d", i);
        int fd = open(path, O_RDWR | O_CLOEXEC);
        if (fd < 0) continue;

        drmModeRes *res = drmModeGetResources(fd);
        if (!res) { close(fd); continue; }

        for (int c = 0; c < res->count_connectors; c++) {
            drmModeConnector *conn = drmModeGetConnector(fd, res->connectors[c]);
            if (!conn) continue;
            if (conn->connection == DRM_MODE_CONNECTED && conn->count_modes > 0) {
                drmModeModeInfo m = conn->modes[0];
                if ((m.hdisplay == 2170 && m.vdisplay == 60) ||
                    (m.hdisplay == 60 && m.vdisplay == 2170)) {
                    hw->drm_fd = fd;
                    hw->conn_id = conn->connector_id;
                    hw->mode = m;
                    hw->width = m.hdisplay;
                    hw->height = m.vdisplay;
                    if (conn->encoder_id) {
                        drmModeEncoder *enc = drmModeGetEncoder(fd, conn->encoder_id);
                        if (enc) { hw->crtc_id = enc->crtc_id; drmModeFreeEncoder(enc); }
                    }
                    if (!hw->crtc_id && res->count_crtcs > 0) {
                        hw->crtc_id = res->crtcs[0];
                    }
                    drmModeFreeConnector(conn);
                    drmModeFreeResources(res);
                    goto found_drm;
                }
            }
            drmModeFreeConnector(conn);
        }
        drmModeFreeResources(res);
        close(fd);
    }
    return -1;

found_drm:
    {
        struct drm_mode_create_dumb creq = {0};
        creq.width = hw->width;
        creq.height = hw->height;
        creq.bpp = 32;
        if (drmIoctl(hw->drm_fd, DRM_IOCTL_MODE_CREATE_DUMB, &creq) < 0) return -2;
        hw->handle = creq.handle;
        hw->pitch = creq.pitch;
        hw->size = creq.size;

        if (drmModeAddFB(hw->drm_fd, hw->width, hw->height, 24, 32, hw->pitch, hw->handle, &hw->fb_id))
            return -3;

        struct drm_mode_map_dumb mreq = {0};
        mreq.handle = hw->handle;
        if (drmIoctl(hw->drm_fd, DRM_IOCTL_MODE_MAP_DUMB, &mreq)) return -4;

        hw->map = mmap(0, hw->size, PROT_READ | PROT_WRITE, MAP_SHARED, hw->drm_fd, mreq.offset);
        if (hw->map == MAP_FAILED) return -5;

        drmModeSetCrtc(hw->drm_fd, hw->crtc_id, hw->fb_id, 0, 0, &hw->conn_id, 1, &hw->mode);
    }

    open_touch_device(hw);
    open_uinput_device(hw);
    return 0;
}

/*
 * Non-blocking touch poll:
 * Returns 1 on finger down, 2 on drag/move, 0 on finger up, -1 if no event.
 * *out_x is normalized to 0..2169 along the Touch Bar horizontal axis.
 */
int tuxbar_hw_poll_touch(TuxBarHW *hw, int *out_x) {
    if (!hw || hw->touch_fd < 0 || !out_x) return -1;
    struct input_event ev;
    int event_kind = -1;

    while (read(hw->touch_fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
        if (ev.type == EV_ABS) {
            if (ev.code == ABS_MT_POSITION_X || ev.code == ABS_X) {
                hw->cur_raw_x = ev.value;
            } else if (ev.code == ABS_MT_POSITION_Y || ev.code == ABS_Y) {
                hw->cur_raw_y = ev.value;
            } else if (ev.code == ABS_MT_TRACKING_ID) {
                if (ev.value >= 0) {
                    hw->touching = 1;
                    event_kind = 1;
                } else {
                    hw->touching = 0;
                    event_kind = 0;
                }
            }
        } else if (ev.type == EV_KEY && ev.code == BTN_TOUCH) {
            hw->touching = ev.value ? 1 : 0;
            event_kind = ev.value ? 1 : 0;
        } else if (ev.type == EV_SYN && ev.code == SYN_REPORT && hw->touching && event_kind < 0) {
            event_kind = 2;
        }
    }

    if (event_kind >= 0) {
        int raw = hw->touch_swapped_xy ? hw->cur_raw_y : hw->cur_raw_x;
        int maxv = hw->touch_swapped_xy ? hw->touch_max_y : hw->touch_max_x;
        if (maxv <= 0) maxv = 2170;
        int x = (int)((int64_t)raw * 2170 / maxv);
        if (x < 0) x = 0;
        if (x >= 2170) x = 2169;
        *out_x = x;
    }
    return event_kind;
}

void tuxbar_hw_send_key(TuxBarHW *hw, uint16_t keycode, uint16_t mod_code) {
    if (!hw || hw->uinput_fd < 0) return;
    if (mod_code) emit_key(hw->uinput_fd, EV_KEY, mod_code, 1);
    emit_key(hw->uinput_fd, EV_KEY, keycode, 1);
    emit_key(hw->uinput_fd, EV_SYN, SYN_REPORT, 0);
    usleep(8000);
    emit_key(hw->uinput_fd, EV_KEY, keycode, 0);
    if (mod_code) emit_key(hw->uinput_fd, EV_KEY, mod_code, 0);
    emit_key(hw->uinput_fd, EV_SYN, SYN_REPORT, 0);
}

int tuxbar_hw_blit(TuxBarHW *hw, const uint32_t *argb_2170x60) {
    if (!hw || !hw->map || !argb_2170x60) return -1;
    uint32_t *dst = (uint32_t *)hw->map;
    uint32_t stride_px = hw->pitch / 4;

    if (hw->width == 2170 && hw->height == 60) {
        for (int y = 0; y < 60; y++) {
            memcpy(dst + y * stride_px, argb_2170x60 + y * 2170, 2170 * 4);
        }
    } else if (hw->width == 60 && hw->height == 2170) {
        for (int y = 0; y < 60; y++) {
            for (int x = 0; x < 2170; x++) {
                dst[x * stride_px + (59 - y)] = argb_2170x60[y * 2170 + x];
            }
        }
    }
    drmModeDirtyFB(hw->drm_fd, hw->fb_id, NULL, 0);
    return 0;
}

void tuxbar_hw_close(TuxBarHW *hw) {
    if (!hw) return;
    if (hw->map && hw->map != MAP_FAILED) munmap(hw->map, hw->size);
    if (hw->fb_id) drmModeRmFB(hw->drm_fd, hw->fb_id);
    if (hw->drm_fd >= 0) close(hw->drm_fd);
    if (hw->uinput_fd >= 0) {
        ioctl(hw->uinput_fd, UI_DEV_DESTROY);
        close(hw->uinput_fd);
    }
    if (hw->touch_fd >= 0) close(hw->touch_fd);
}
#endif
