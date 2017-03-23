#!/bin/bash

# Copyright 2017 Google Inc.
# Copyright 2015 The Android Open Source Project
# Copyright (C) 2015 Valve Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ -z "$1" ]
  then
    echo "Usage: fuchsia-generate.sh OUTPUT_DIR"
    exit 1
fi

SOURCE_DIR=$(cd -P -- "$(dirname -- "$0")" && pwd -P)
OUTPUT_DIR=$1
rm -rf $OUTPUT_DIR/generated
mkdir -p $OUTPUT_DIR/generated/include

python $SOURCE_DIR/../scripts/vk_helper.py --gen_struct_wrappers $SOURCE_DIR/../include/vulkan/vulkan.h --abs_out_dir $OUTPUT_DIR/generated/include > /dev/null

( cd $OUTPUT_DIR/generated/include; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml vk_enum_string_helper.h 2> /dev/null)
( cd $OUTPUT_DIR/generated/include; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml vk_dispatch_table_helper.h 2> /dev/null)
( cd $OUTPUT_DIR/generated/include; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml thread_check.h 2> /dev/null )
( cd $OUTPUT_DIR/generated/include; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml parameter_validation.h 2> /dev/null)
( cd $OUTPUT_DIR/generated/include; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml unique_objects_wrappers.h 2> /dev/null)
