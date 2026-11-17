CC := gcc
CFLAGS := -O2 -Wall -Wextra -fPIC -shared $(shell pkg-config --cflags libdrm 2>/dev/null || echo "-I/usr/include/libdrm")
LDFLAGS := $(shell pkg-config --libs libdrm 2>/dev/null || echo "-ldrm")

.PHONY: all clean previews

all: build/libtuxbar_hw.so

build/libtuxbar_hw.so: src/tuxbar_hw.c
	@mkdir -p build
	$(CC) $(CFLAGS) src/tuxbar_hw.c -o build/libtuxbar_hw.so $(LDFLAGS)

previews:
	python3 -m tuxbar_pro.main --export-previews assets/strips

clean:
	rm -rf build
