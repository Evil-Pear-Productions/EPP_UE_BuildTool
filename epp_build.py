"""
Evil Pear Productions Unreal Build Tool
@author Connor McCloskey

See the ReadMe for full information.
"""

#region --- Imports ---

import os
import platform
import subprocess
import sys
import json
from zipfile import ZipFile
import shutil
from datetime import datetime

#endregion

#region --- Vars ---

#region - Per Project -

""" TODO - Change these for your project! Can also be set via command line args """

project_name:           str = "MyGame"                                      # Uproject file name
project_path:           str = "D:\\MyGameProjects\\MyGame"                  # Path to the project file
builds_path:            str = "D:\\MyGameProjects\\Builds\\MyGameBuilds"    # Directory where you wish builds to be archived at
engine_path:            str = "C:\\Program Files\\Epic Games\\UE_5.4"       # Path to your desired Unreal Engine version
build_config:           str = "Development"                                 # Desired build config (DebugGame, Development, or Shipping)
build_platform:         str = "Win64"                                       # Desired platform
cook_command:           str = "BuildCookRun"                                # Specific cook command
update_ue_config:       bool = True                                         # Specifies if we should update the UE DefaultGame config file's project version field
architecture:           str = "x86_64"

#endregion

#region - Generated -

new_version:            str = ""    # New version name
archive_path:           str = ""    # Generated directory where the packaged project should be placed
uat_path:               str = ""    # Generated path to the RunUAT batch file

#endregion

#region - Constants -

uat_path_base_win:      str = "Engine\\Build\\BatchFiles\\RunUAT.bat"           # Sub path to UE's RunUAT batch file
uat_path_base_mac:      str = "Engine/Build/BatchFiles/RunUAT.command"          # Sub path to UE's RunUAT command file
uat_path_base_linux:    str = "Engine/Build/BatchFiles/RunUAT.sh"               # Sub path to UE's RunUAT shell file
version_section:        str = "/Script/EngineSettings.GeneralProjectSettings"   # Game version section in UE DefaultGame config file
build_config_name:      dict = {
    "Development":      "dev",
    "DebugGame":        "debug",
    "Shipping":         "shipping"
}
settings_file_name:     str = "settings.json"

#endregion

#endregion

#region --- Class ---

### VERY basic class for manually parsing an Unreal config file, because of course, why would we follow ini standards???
class UnrealConfig:

    sections:           dict = {}
    all_option_keys:    list = []
    path:               str = ""

    ### Goes through the option and gets it to copy EXACTLY as it would be from the UE file...
    ### We want to make sure we don't cause more source control changes than needed
    def parse_option(self, line):
        delimit = line.split("=", 1)

        key = delimit[0]
        key = key.lstrip()
        key = key.rstrip()
        self.all_option_keys.append(key)
        value = delimit[1]
        value = value.rstrip()
        value = value.lstrip()

        return [key, value]

    def parse_file(self, filepath):
        file = open(filepath, 'r')
        config_lines = file.readlines()
        file.close()

        self.path = filepath

        current_section = ""

        for index in range(0, len(config_lines)):
            line = config_lines[index].strip()
            if line == "":
                continue
            if line.startswith('[') and line.endswith(']'):
                current_section = line
                self.sections[current_section] = []
            else:
                if current_section == "":
                    continue
                opt = self.parse_option(line)
                self.sections[current_section].append(opt)

    def has_section(self, section):
        if section in self.sections:
            return True
        return False

    def has_option(self, section, option):
        section = self.sanitize_section(section)
        if section in self.sections:
            options = self.sections[section]
            for opt in options:
                key = opt[0]
                if key == option:
                    return True
        return False

    def has_option_anywhere(self, option):
        if option in self.all_option_keys:
            return True
        return False

    def update_option(self, section, option, new_value):
        section = self.sanitize_section(section)
        options = self.sections[section]
        for opts in options:
            key = opts[0]
            if key == option:
                opts[1] = new_value

    def add_option(self, section, option):
        section = self.sanitize_section(section)
        self.sections[section].append(option)

    def get_option_value(self, section, option):
        section = self.sanitize_section(section)
        if self.has_option(section, option):
            options = self.sections[section]
            for opt in options:
                key = opt[0]
                if key == option:
                    value = opt[1]
                    return value
        return ""

    def sanitize_section(self, section):
        r = section[0]
        l = section[len(section) - 1]
        if r != "[":
            section = "[" + section
        if l != "]":
            section = section + "]"
        return section

    def update_file(self):
        file = open(self.path, 'w')
        # file = open("text.txt", "w")
        for key in self.sections:
            file.write(key + "\n")
            options = self.sections[key]
            for opt in options:
                k = opt[0]
                v = opt[1]
                line = k + "=" + v + "\n"
                file.write(line)
            file.write("\n")
        file.close()

    def display(self):
        print("")
        for key in self.sections:
            print(key)
            options = self.sections[key]
            for opt in options:
                k = opt[0]
                v = opt[1]
                line = k + "=" + v
                print(line)
            print("")

#endregion

#region --- Functions ---

#region - Set script global vars -
def set_new_version(v: str):
    global new_version
    new_version = v
    print(">> New version number:      ", v)

def set_project_path(path: str):
    global project_path
    project_path = path

def set_project_name(name: str):
    global project_name
    project_name = name

def set_build_path(path: str):
    global builds_path
    builds_path = path

def set_build_config(build_type: str):
    global build_config
    build_config = build_type

def set_cook_command(cmd: str):
    global cook_command
    cook_command = cmd

def set_build_platform(p: str):
    global build_platform
    build_platform = p

def set_engine_path(path: str):
    global engine_path
    engine_path = path
    construct_uat_path()

def set_update_ue_flag(flag: bool):
    global update_ue_config
    update_ue_config = flag

def set_architecture(arch: str):
    global architecture
    architecture = arch

def print_settings():
    print(">> Set project name:        ", project_name)
    print(">> Set project path:        ", project_path)
    print(">> Set UAT path:            ", uat_path)
    print(">> Set build path to:       ", builds_path)
    print(">> Set build configuration: ", build_config)
    print(">> Set cook command:        ", cook_command)
    print(">> Set build platform:      ", build_platform)
    print(">> Update UE config file?   ", update_ue_config)
    print(">> Set architecture:        ", architecture)

def construct_uat_path():
    subpath = uat_path_base_win
    if platform.system() == "Darwin":
        subpath = uat_path_base_mac
    elif platform.system() == "Linux":
        subpath = uat_path_base_linux
    global uat_path
    uat_path = os.path.join(engine_path, subpath)
#endregion

#region - Process funcs -
def make_archive_path():
    print("")
    print(">>>>> Creating archive directory...")

    global archive_path

    new_directory = os.path.join(builds_path, new_version)
    archive_path = new_directory
    if os.path.exists(new_directory):
        print(">> Directory already exists, early returning...")
        return
    os.mkdir(new_directory)

def save_config(config, config_path):
    configfile = open(config_path, 'w')
    config.write(configfile)
    configfile.close()

def update_version():
    # EPP uses a standardized versioning name convention:
    # date_buildconfig_num
    # E.g. 042625_dev_001 indicates the build was on 04.26.25, on Development, first build of the day
    # This is then used to make our build directory

    # Config is stored in the DefaultGame.ini file,
    # section [/Script/EngineSettings.GeneralProjectSettings]
    # as ProjectVersion=042625_dev_001

    # If you/your team use a different standard, feel free to update this as needed!

    print("")
    print(">>>>> Updating Unreal DefaultGame config file...")

    build_date = datetime.today().strftime('%m%d%y')

    config_file_path = os.path.join(project_path, "Config\\DefaultGame.ini")

    if not os.path.exists(config_file_path):
        print("!! WARNING !! COULD NOT FIND CONFIG FILE! Path: ", config_file_path)
        exit_tool(1)

    build = build_config_name[build_config]
    version = ""

    config = UnrealConfig()
    config.parse_file(config_file_path)

    # Check to see if option exists or not
    if config.has_option(version_section, "ProjectVersion"):
        last_version = config.get_option_value(version_section, "ProjectVersion")
        split = last_version.split("_")  # Returns 3 elements
        last_build_date = split[0]

        # If the dates don't match, we just start at '001'
        if last_build_date != build_date:
            version = build_date + "_" + build + "_001"
            config.update_option(version_section, "ProjectVersion", version)
        else:
            new_build_int = int(split[2]) + 1
            new_build_formatted = "{:03d}".format(new_build_int)
            version = build_date + "_" + build + "_" + new_build_formatted
            config.update_option(version_section, "ProjectVersion", version)
    else:
        version = build_date + "_" + build + "_001"
        config.add_option(version_section, ["ProjectVersion", version])

    config.update_file()
    set_new_version(version)

def read_settings_json():

    print(">>>>> Importing settings from JSON")

    if not os.path.exists(settings_file_name):
        print(">>>>> No settings file found, using script defaults")
        construct_uat_path()
        return

    file = open(settings_file_name, "r")
    settings = json.load(file)
    file.close()

    set_project_path(settings["projectpath"])
    set_project_name(settings["projectname"])
    set_engine_path(settings["enginepath"])
    set_build_path(settings["buildpath"])
    set_build_config(settings["buildconfig"])
    set_cook_command(settings["cookcommand"])
    set_build_platform(settings["buildplatform"])
    set_update_ue_flag(settings["updategame"])
    set_architecture(settings["architecture"])

def write_settings_json():

    print("")
    print(">>>>> Writing settings to JSON")

    new_settings = {
        "projectpath": project_path,
        "projectname": project_name,
        "enginepath": engine_path,
        "buildpath": builds_path,
        "buildconfig": build_config,
        "cookcommand": cook_command,
        "buildplatform": build_platform,
        "updategame": update_ue_config,
        "architecture": architecture
    }

    json_data = json.dumps(new_settings, indent=4)

    file = open(settings_file_name, "w")
    file.write(json_data)
    file.close()

def make_zip():
    zip_result = shutil.make_archive(archive_path, 'zip', archive_path)
    final = shutil.move(zip_result, archive_path)
    print(">>>>>> ZIP result: " + final)

def make_build():

    print("")
    print(">>>>> Starting build process")

    if update_ue_config:
        update_version()

    make_archive_path()
    build_command = [
        uat_path,
        cook_command,
        f"-project={os.path.join(project_path, f'{project_name}.uproject')}",
        "-noP4",
        f"-platform={build_platform}",
        f"-specifiedarchitecture={architecture}",
        f"-clientconfig={build_config}",
        "-cook",
        "-build",
        "-stage",
        "-pak",
        "-archive",
        f"-archivedirectory={archive_path}"
    ]

    if build_platform != "Win64":
        build_command.append("-client")

    print("")
    print(">>>>> Packaging game...")
    print("")

    try:
        result = subprocess.run(build_command, shell=True, check=True)
        print("")
        print(">>>>> PACKAGING DONE! Return code: ", result.returncode)
        print(">>>>> Packaging build into ZIP...")
        make_zip()
        exit_tool(0)
    except subprocess.CalledProcessError as e:
        print("")
        print(">>>>> PACKAGING FAILED: ", e)
        exit_tool(1)

def helpme():
    print("""
    *** EPP Build Tool commands ***
        helpme                  Prints this info. Congrats, you did it!

        updatesettingsonly      Don't run the build, just update the settings and save out to JSON. If not specified, will try to run the build process.
                                Does not take in any additional info, and will override anything passed into a "savesettings" argument

        savesettings            If true, will save out the inputted settings to JSON, which will be read in as the new defaults in the future. Defaults to false.

        updategame              Flag if we should update the UE DefaultGame ini file's project version. True by default.
        buildconfig             Set the build config of the Unreal project (Development, DebugGame, or Shipping)
        enginepath              Set the path to your Unreal Engine install
        projectname             Set the game project name (name of your .uproject file)
        projectpath             Set the game's project path (path where your .uproject file exists)
        buildpath               Set path of where to archive the packaged game (path where the build goes!)
        buildplatform           Set the platform to build for (by default set to Win64)
        cookcommand             Specify the cook command to use (by default uses BuildCookRun)
        architecture            Specify which architecture(s) to build for ('x86_64', 'arm64', or 'arm64+x86_64')
    *******************************
    """)

def exit_tool(code: int):
    print("")
    print(">>>>>>>>>> EXITING EPP UNREAL BUILD TOOL <<<<<<<<<<")
    print("")
    sys.exit(code)

def process_args():

    num_args = len(sys.argv)

    # First, if no args, we assume it's just a standard build with the saved/current settings
    if num_args == 0:
        make_build()
        return

    # Operation flags
    update_settings_only: bool = False
    save_settings: bool = False

    valid_args = [
        "helpme",
        "updatesettingsonly",
        "savesettings",
        "updategame",
        "buildconfig",
        "enginepath",
        "projectname",
        "projectpath",
        "buildpath",
        "buildplatform",
        "cookcommand",
        "architecture",
        "generatesettings"
    ]

    # Go through the array of sys args and sort them into key-value pairs for ease-of-use
    sorted_args: dict = {}
    index = 1
    while index <= num_args - 1:
        key = sys.argv[index].lower()
        print("Current key: ", key)
        if key not in valid_args:
            print("!!! WARNING !!! Invalid argument: '" + key + "'. Use 'helpme' for a list of all valid commands!")
            exit_tool(0)
        elif key == "helpme":
            helpme()
            exit_tool(0)
        elif key == "updatesettingsonly" or key == "generatesettings":
            update_settings_only = True
            save_settings = True
            sorted_args[key] = "True" # Do this just to follow the format
            index += 1
            continue
        value = sys.argv[index + 1]
        sorted_args[key] = value
        index += 2

    print("")
    print(">>>>> Processing command line arguments")

    # Now, go through any settings that were passed in and update them
    # Determine if we should save settings
    if update_settings_only == False and "savesettings" in sorted_args:
        v = sorted_args["savesettings"]
        if v.lower() == "true":
            save_settings = True

    # Set project name
    if "projectname" in sorted_args:
        v = sorted_args["projectname"]
        set_project_name(v)

    # Set project path
    if "projectpath" in sorted_args:
        v = sorted_args["projectpath"]
        set_project_path(v)

    # Set UAT path
    if "enginepath" in sorted_args:
        v = sorted_args["enginepath"]
        set_engine_path(v)

    # Set build path
    if "buildpath" in sorted_args:
        v = sorted_args["buildpath"]
        set_build_path(v)

    # Set build config
    if "buildconfig" in sorted_args:
        v = sorted_args["buildconfig"].lower()
        if v == "dev" or v == "development":
            set_build_config("Development")
        elif v == "debug" or v == "debuggame":
            set_build_config("DebugGame")
        elif v == "shipping":
            set_build_config("Shipping")
        else:
            set_build_config("Development")

    # Set cook command
    if "cookcommand" in sorted_args:
        v = sorted_args["cookcommand"]
        set_cook_command(v)

    # Set build platform
    if "buildplatform" in sorted_args:
        v = sorted_args["buildplatform"]
        set_build_platform(v)

    # Flag for updating UE config file
    if "updategame" in sorted_args:
        v = sorted_args["updategame"]
        if v.lower() == "false":
            set_update_ue_flag(False)

    # Set build architecture(s)
    if "architecture" in sorted_args:
        v = sorted_args["architecture"]
        set_architecture(v)

    # Now, if we were told to only update the settings, return and exit. Else, make the build!
    if update_settings_only:
        write_settings_json()

        print("")
        print("** Updated settings **")
        print_settings()

        print("")
        print(">>>>> Settings update complete")

        exit_tool(0)
    else:
        if save_settings:
            write_settings_json()
            print("")
            print("** Updated build settings **")
        else:
            print("")
            print("** Build Settings **")
        print_settings()
        make_build()

def start_tool():

    print("")
    print(">>>>>>>>>> RUNNING EPP UNREAL BUILD TOOL <<<<<<<<<<")
    print("")

    read_settings_json()
    process_args()
#endregion

#endregion

#region --- Main ---

def main():
    start_tool()

#endregion

if __name__ == "__main__":
    main()
