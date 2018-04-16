# Vulkan Loader and Validation Layers on Fuchsia

- The `BUILD.gn` files are for building as a part of Fuchsia using `GN`.
- The `build-fuchsia` directory contains customized scripts to generate some of
the necessary header files. These header files are pre-generated and used in the
root `BUILD.gn` file.
- To regenerate the header files after an update, run the following command:
```
cd $FUCHSIA_ROOT/third_party/vulkan_loader_and_validation_layers
./build-fuchsia/fuchsia-generate.sh build-fuchsia
```
- Synchronize layer descriptions; see layers/fuchsia/README.md

- The header files `vulkan.h` and `vulkan.hpp` are generated from `vk.xml`. If
`vk.xml` changes, regenerate the files with the following steps:

```
# Before you start, $FUCHSIA_ROOT must point to the root of your
# Fuchsia checkout. Then use that to set $VULKAN_LOADER_SOURCE:
export VULKAN_LOADER_SOURCE=$FUCHSIA_ROOT/third_party/vulkan_loader_and_validation_layers

# Check out Vulkan-Hpp repository
#
# NOTE: using commit bea247fd4e645579cda228d672ba815292015c75 is known to work;
# a following change breaks escher because of disabled exceptions: see
# https://github.com/KhronosGroup/Vulkan-Hpp/issues/113
#
git clone --recursive https://github.com/KhronosGroup/Vulkan-Hpp.git
cd Vulkan-Hpp

# Copy over our version of vk.xml
cp $VULKAN_LOADER_SOURCE/scripts/vk.xml Vulkan-Docs/src/spec/vk.xml

# Generate header files from vk.xml
cmake . && make && ./VulkanHppGenerator
(cd Vulkan-Docs/src/spec && make clobber install)

# Copy the header files back to our repo
cp vulkan/vulkan.hpp $VULKAN_LOADER_SOURCE/include/vulkan/vulkan.hpp
cp Vulkan-Docs/src/vulkan/vulkan.h $VULKAN_LOADER_SOURCE/include/vulkan/vulkan.h
```
