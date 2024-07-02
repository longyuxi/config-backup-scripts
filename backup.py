import platform
from pathlib import Path
import yaml
import shutil
import subprocess
import json

from functional import seq

import uploadutils

def copy_files_specified_by_yaml(yaml_file, destination_folder):
    with open(yaml_file) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

    files = seq(data['files']).map(lambda x: Path(x)).map(lambda x: x.expanduser()).list()
    folders = seq(data['folders']).map(lambda x: Path(x)).map(lambda x: x.expanduser()).list()

    # Copy files
    for file in files:
        shutil.copy(file, destination_folder)

def generate_brew_list(destination_folder):
    # Capture output of cat ~/.zsh_history | grep brew
    cat = subprocess.Popen(('cat', str(Path('~/.zsh_history').expanduser())), stdout=subprocess.PIPE)
    output = subprocess.check_output(('grep', 'brew'), stdin=cat.stdout)
    cat.wait()

    with open(destination_folder / 'zsh_history_brew.txt', 'wb') as f:
        f.write(output)

def generate_conda_list(destination_folder):
    envs_save_folder = destination_folder / 'conda_envs'
    envs_save_folder.mkdir(exist_ok=True)

    conda_exe = '/Users/longyuxi/miniforge3/condabin/mamba'

    envs_json = subprocess.check_output([conda_exe, 'env', 'list', '--json'])
    envs = json.loads(envs_json)

    for env in envs['envs']:
        env_name = Path(env).name
        print(env_name)
        env_export = subprocess.check_output([conda_exe, 'env', 'export', '-n', env_name, '--from-history'])

        env_shortname = env_name.split('/')[-1]
        with open(envs_save_folder / f'{env_shortname}.yaml', 'wb') as f:
            f.write(env_export)


def upload(source_folder, destination_folder, temporary_folder='tempupload', compress=False, use_absolute_paths_in_archive=False, folder_size_threshold_gb=1, number_to_keep=10):
    uploadutils.make_archives(
        source_folder,
        folder_size_threshold_gb=folder_size_threshold_gb,
        temporary_folder=temporary_folder,
        compress=compress,
        use_absolute_paths_in_archive=use_absolute_paths_in_archive)
    uploadutils.update_archives(temporary_folder, destination_folder, number_to_keep)
    shutil.rmtree(temporary_folder)

if __name__ == '__main__':
    if platform.node() == 'Prix.local':
        TEMPORARY_FOLDER = Path('/Users/longyuxi/Downloads/config-backup-temporary-folder')
        TEMPORARY_FOLDER.mkdir(exist_ok=True)

        INCLUDE_YAML = Path('mac-include.yaml')

        copy_files_specified_by_yaml(INCLUDE_YAML, TEMPORARY_FOLDER)
        generate_brew_list(TEMPORARY_FOLDER)
        generate_conda_list(TEMPORARY_FOLDER)

        DESTINATION_FOLDER =  'onedrive:backup/mac/configs/'

        upload(TEMPORARY_FOLDER, DESTINATION_FOLDER)


    else:
        raise NotImplementedError
