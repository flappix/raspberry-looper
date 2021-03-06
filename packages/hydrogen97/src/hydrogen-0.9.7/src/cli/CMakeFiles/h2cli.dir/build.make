# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.18

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:


#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:


# Disable VCS-based implicit rules.
% : %,v


# Disable VCS-based implicit rules.
% : RCS/%


# Disable VCS-based implicit rules.
% : RCS/%,v


# Disable VCS-based implicit rules.
% : SCCS/s.%


# Disable VCS-based implicit rules.
% : s.%


.SUFFIXES: .hpux_make_needs_suffix_list


# Command-line flag to silence nested $(MAKE).
$(VERBOSE)MAKESILENT = -s

#Suppress display of executed commands.
$(VERBOSE).SILENT:

# A target that is always out of date.
cmake_force:

.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /usr/bin/cmake

# The command to remove a file.
RM = /usr/bin/cmake -E rm -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7

# Include any dependencies generated for this target.
include src/cli/CMakeFiles/h2cli.dir/depend.make

# Include the progress variables for this target.
include src/cli/CMakeFiles/h2cli.dir/progress.make

# Include the compile flags for this target's objects.
include src/cli/CMakeFiles/h2cli.dir/flags.make

src/cli/CMakeFiles/h2cli.dir/main.cpp.o: src/cli/CMakeFiles/h2cli.dir/flags.make
src/cli/CMakeFiles/h2cli.dir/main.cpp.o: src/cli/main.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object src/cli/CMakeFiles/h2cli.dir/main.cpp.o"
	cd /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/h2cli.dir/main.cpp.o -c /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli/main.cpp

src/cli/CMakeFiles/h2cli.dir/main.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/h2cli.dir/main.cpp.i"
	cd /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli/main.cpp > CMakeFiles/h2cli.dir/main.cpp.i

src/cli/CMakeFiles/h2cli.dir/main.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/h2cli.dir/main.cpp.s"
	cd /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli/main.cpp -o CMakeFiles/h2cli.dir/main.cpp.s

# Object files for target h2cli
h2cli_OBJECTS = \
"CMakeFiles/h2cli.dir/main.cpp.o"

# External object files for target h2cli
h2cli_EXTERNAL_OBJECTS =

src/cli/h2cli: src/cli/CMakeFiles/h2cli.dir/main.cpp.o
src/cli/h2cli: src/cli/CMakeFiles/h2cli.dir/build.make
src/cli/h2cli: src/core/libhydrogen-core-0.9.7.so
src/cli/h2cli: /usr/lib/libQtGui.so
src/cli/h2cli: /usr/lib/libQtCore.so
src/cli/h2cli: /usr/lib/libQtXml.so
src/cli/h2cli: /usr/lib/libQtXmlPatterns.so
src/cli/h2cli: /usr/lib/libarchive.so
src/cli/h2cli: /usr/lib/libsndfile.so
src/cli/h2cli: /usr/lib/libasound.so
src/cli/h2cli: /usr/lib/libjack.so
src/cli/h2cli: /usr/lib/libpulse.so
src/cli/h2cli: /usr/lib/liblrdf.so
src/cli/h2cli: /usr/lib/libz.so
src/cli/h2cli: /usr/lib/liblo.so
src/cli/h2cli: src/cli/CMakeFiles/h2cli.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Linking CXX executable h2cli"
	cd /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli && $(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/h2cli.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
src/cli/CMakeFiles/h2cli.dir/build: src/cli/h2cli

.PHONY : src/cli/CMakeFiles/h2cli.dir/build

src/cli/CMakeFiles/h2cli.dir/clean:
	cd /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli && $(CMAKE_COMMAND) -P CMakeFiles/h2cli.dir/cmake_clean.cmake
.PHONY : src/cli/CMakeFiles/h2cli.dir/clean

src/cli/CMakeFiles/h2cli.dir/depend:
	cd /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7 && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7 /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7 /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli /home/flappix/docs/code/raspberry-looper/packages/hydrogen97/src/hydrogen-0.9.7/src/cli/CMakeFiles/h2cli.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : src/cli/CMakeFiles/h2cli.dir/depend

