/*
 *
 * Copyright (c) 2018 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#include "dlopen_fuchsia.h"

#include <fcntl.h>
#include <fdio/io.h>
#include <stdio.h>
#include <zircon/dlfcn.h>
#include <zircon/syscalls.h>

void *dlopen_fuchsia(const char *name, int mode) {
    char path[PATH_MAX];
    if (snprintf(path, sizeof(path), "/system/lib/%s", name) >= PATH_MAX) {
        return NULL;
    }
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        return NULL;
    }
    zx_handle_t vmo = ZX_HANDLE_INVALID;
    zx_status_t status = fdio_get_vmo_clone(fd, &vmo);
    close(fd);
    if (status != ZX_OK) {
        return NULL;
    }
    void *result = dlopen_vmo(vmo, mode);
    zx_handle_close(vmo);
    return result;
}
