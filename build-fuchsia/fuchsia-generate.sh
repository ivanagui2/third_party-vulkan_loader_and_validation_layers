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
    echo "Usage: fuchsia-generate.sh TARGET_GEN_DIR"
    exit 1
fi

function realpath { echo $(cd -P $(dirname $1); pwd)/$(basename $1); }
# Get full path for the parent of this script
SOURCE_DIR=$(realpath $(dirname $0))
# Get full path for our gen directory
OUTPUT_DIR=$(realpath $1)
OUTPUT_INCLUDE_DIR=$OUTPUT_DIR/generated/include

rm -rf $OUTPUT_DIR/generated
mkdir -p $OUTPUT_INCLUDE_DIR

( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_safe_struct.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_safe_struct.cpp 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_struct_size_helper.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_struct_size_helper.c 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_enum_string_helper.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_object_types.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_dispatch_table_helper.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR thread_check.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR parameter_validation.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR unique_objects_wrappers.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_loader_extensions.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_loader_extensions.c 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_layer_dispatch_table.h 2> /dev/null )
( cd $SOURCE_DIR; python $SOURCE_DIR/../scripts/lvl_genvk.py -registry $SOURCE_DIR/../scripts/vk.xml -o $OUTPUT_INCLUDE_DIR vk_extension_helper.h 2> /dev/null )
