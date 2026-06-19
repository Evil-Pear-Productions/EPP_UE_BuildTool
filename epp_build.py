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
build_platforms:        list = ["Win64", "Linux"]                           # Desired platforms
cook_command:           str = "BuildCookRun"                                # Specific cook command
update_ue_config:       bool = True                                         # Specifies if we should update the UE DefaultGame config file's project version field
architecture:           str = "x86_64"

#endregion

#region - Generated -

new_version:            str = ""                                            # New version name
archive_path:           str = ""                                            # Generated directory where the packaged project should be placed
uat_path:               str = ""                                            # Generated path to the RunUAT batch file

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
def set_new_version(v: str) -> None:
    global new_version
    new_version = v
    print(">> New version number:      ", v)

def set_project_path(path: str) -> None:
    global project_path
    project_path = path

def set_project_name(name: str) -> None:
    global project_name
    project_name = name

def set_build_path(path: str) -> None:
    global builds_path
    builds_path = path

def set_build_config(build_type: str) -> None:
    global build_config
    build_config = build_type

def set_cook_command(cmd: str) -> None:
    global cook_command
    cook_command = cmd

def set_build_platforms(p: list) -> None:
    global build_platforms
    build_platforms = p

def set_engine_path(path: str) -> None:
    global engine_path
    engine_path = path
    construct_uat_path()

def set_update_ue_flag(flag: bool) -> None:
    global update_ue_config
    update_ue_config = flag

def set_architecture(arch: str) -> None:
    global architecture
    architecture = arch

def print_settings() -> None:
    print(">> Set project name:        ", project_name)
    print(">> Set project path:        ", project_path)
    print(">> Set UAT path:            ", uat_path)
    print(">> Set build path to:       ", builds_path)
    print(">> Set build configuration: ", build_config)
    print(">> Set cook command:        ", cook_command)
    print(">> Set build platform:      ", build_platforms)
    print(">> Update UE config file?   ", update_ue_config)
    print(">> Set architecture:        ", architecture)

def construct_uat_path() -> None:
    subpath = uat_path_base_win
    if platform.system() == "Darwin":
        subpath = uat_path_base_mac
    elif platform.system() == "Linux":
        subpath = uat_path_base_linux
    global uat_path
    uat_path = os.path.join(engine_path, subpath)
#endregion

#region - Process funcs -
def make_archive_path() -> None:
    print("")
    print(">>>>> Creating archive directory...")

    global archive_path

    new_directory = os.path.join(builds_path, new_version)
    archive_path = new_directory
    if os.path.exists(new_directory):
        print(">> Directory already exists, early returning...")
        return
    os.mkdir(new_directory)

def make_archive_path_for_platform(target_platform: str) -> str:
    print("")
    print(f">>>>> Creating archive directory for platform {target_platform}...")

    global archive_path

    new_directory = os.path.join(archive_path, target_platform)
    if os.path.exists(new_directory):
        print(">> Directory already exists, early returning...")
        return new_directory
    os.mkdir(new_directory)
    return new_directory

def save_config(config, config_path) -> None:
    configfile = open(config_path, 'w')
    config.write(configfile)
    configfile.close()

def update_version() -> None:
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

def read_settings_json() -> None:

    print(">>>>> Importing settings from JSON")

    file = open(settings_file_name, "r")
    settings = json.load(file)
    file.close()

    set_project_path(settings["project_path"])
    set_project_name(settings["project_name"])
    set_engine_path(settings["engine_path"])
    set_build_path(settings["build_path"])
    set_build_config(settings["build_config"])
    set_cook_command(settings["cook_command"])
    set_build_platforms(settings["build_platforms"])
    set_update_ue_flag(settings["should_update_version_config"])
    set_architecture(settings["architecture"])

def write_settings_json() -> None:

    print("")
    print(">>>>> Writing settings to JSON")

    new_settings = {
        "project_path": project_path,
        "project_name": project_name,
        "engine_path": engine_path,
        "build_path": builds_path,
        "build_config": build_config,
        "cook_command": cook_command,
        "build_platforms": build_platforms,
        "should_update_version_config": update_ue_config,
        "architecture": architecture
    }

    json_data = json.dumps(new_settings, indent=4)

    file = open(settings_file_name, "w")
    file.write(json_data)
    file.close()

def make_zip(target_platform: str, target_path: str) -> None:
    final_name = target_platform.lower()

    if new_version != "":
        final_name = new_version + "_" + final_name

    zip_result = shutil.make_archive(final_name, 'zip', target_path)
    final = shutil.move(zip_result, target_path)
    print(">>>>>> ZIP result: " + final)

def make_build(target_platform:str) -> None:

    target_path = make_archive_path_for_platform(target_platform)

    build_command = [
        uat_path,
        cook_command,
        f"-project={os.path.join(project_path, f'{project_name}.uproject')}",
        "-noP4",
        f"-platform={target_platform}",
        f"-specifiedarchitecture={architecture}",
        f"-clientconfig={build_config}",
        "-cook",
        "-build",
        "-stage",
        "-pak",
        "-archive",
        f"-archivedirectory={target_path}"
    ]

    if target_platform != "Win64":
        build_command.append("-client")

    print("")
    print(f">>>>> Packaging game for {target_platform}...")
    print("")

    try:
        result = subprocess.run(build_command, shell=True, check=True)
        print("")
        print(">>>>> PACKAGING DONE! Return code: ", result.returncode)
        print(">>>>> Packaging build into ZIP...")
        make_zip(target_platform, target_path)
    except subprocess.CalledProcessError as e:
        print("")
        print(">>>>> PACKAGING FAILED: ", e)
        exit_tool(1)

def exit_tool(code: int) -> None:
    print("")
    print(">>>>>>>>>> EXITING EPP UNREAL BUILD TOOL <<<<<<<<<<")
    print("")
    sys.exit(code)

def verify_settings() -> bool:
    if not os.path.exists(settings_file_name):
        return False
    return True

def make_all_builds() -> None:
    print("")
    print(">>>>> Starting build process...")
    print("")

    if update_ue_config:
        update_version()

    make_archive_path()

    for p in build_platforms:
        make_build(p)

    print("")
    print(">>>>> ALL PACKAGING COMPLETE!")
    print("")

    exit_tool(0)

def start_tool() -> None:
    print("")
    print(">>>>>>>>>> RUNNING EPP UNREAL BUILD TOOL <<<<<<<<<<")
    print("")

    if not verify_settings():
        print("**** ALERT **** No settings JSON was found! Use generated template to fill out your settings and try again.")
        write_settings_json()
        exit_tool(0)

    read_settings_json()
    make_all_builds()

#endregion

#endregion

#region --- Main ---

def main() -> None:
    start_tool()

#endregion

if __name__ == "__main__":
    main()
