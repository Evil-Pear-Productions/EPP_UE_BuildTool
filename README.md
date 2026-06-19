# EPP_UE_BuildTool
A simple Python tool to build an Unreal game and auto-update the project version number.

@author Connor McCloskey, Evil Pear Productions

Made with Python 3.12


## About
An easy-to-use script aimed at auto-updating an Unreal `DefaultGame.ini` version number field and then generating builds of the specified UE project on all specified platforms.

We're also open sourcing this script - this is a simple operation that should probably be better integrated into the base engine, so barring engine feature updates to enable that, we've provided *some sort* of option and knowledge repo for doing so.

To use the ini file's ProjectVersion field from C++ or Blueprints, refer to the simple C++ code described here: https://forums.unrealengine.com/t/how-to-get-project-version/487787

This is a great source for additional Unreal Automation Tool info: https://github.com/botman99/ue4-unreal-automation-tool


## Setup
This tool uses a settings file to operate correctly.

If no settings file is found, the tool will generate one for you to fill out and then exit.


## Build Naming Convention
Evil Pear Productions uses a standardized version naming convention:

`date_buildconfig_num`

E.g. `042625_dev_001` indicates the build was on 04.26.25, on Development, first build of the day.

This is then used to make our build directory.

Should your team wish to use a different naming convention, you will need to change the contents of the function `update_version` in the main Python file.


## Settings
* `project_path` - Absolute path where your .uproject file exists
* `project_name` - Name of your .uproject file
* `engine_path` - Absolute path to your Unreal Engine install
* `build_path` - Absolute path of where to archive the packaged project
* `build_config` - Build config to use (Development, DebugGame, or Shipping)
* `build_platforms` - Platform to build for (by default set to Win64 and Linux)
* `cook_command` - Specify the cook command to use (by default uses BuildCookRun)
* `should_update_version_config` - Flag if we should update the UE DefaultGame ini file's project version. True by default.
* `architecture` - Specify the architecture(s) to build for ('x86_64', 'arm64', or 'arm64+x86_64')
