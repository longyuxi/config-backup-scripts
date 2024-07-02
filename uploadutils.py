from pathlib import Path
import subprocess
import platform
import shutil
import time

def du(path):
    """Returns the size of the folder in bytes. Behavior of du command could different on different platforms.
    """
    if platform.system() == 'Darwin':
        return int(subprocess.check_output(['du','-sk', path]).split()[0].decode('utf-8')) * 1024
    else:
        raise NotImplementedError

def make_archives(
        source: str | Path,
        folder_size_threshold_gb: float,
        temporary_folder: str | Path,
        use_absolute_paths_in_archive: bool = False,
        compress: bool = True,
):
    """Main function to run the backup process.

    Args:
        source (str | Path): Source folder to be backed up. Backs up "source/*" to "destination/*".
        folder_size_threshold_gb (float): Threshold for the size of the folder to be backed up. Folders are incrementally added to the tar file until the size exceeds this threshold.
        temporary_folder (str | Path): Temporary folder to store the tar files before uploading to the destination. Needs not to be a subdirectory of source.
        use_absolute_paths_in_archive (bool, optional): If True, uses absolute paths in the tar file. Defaults to False.
        compress (bool, optional): If True, compresses the tar file using gzip. Defaults to True.
    """

    source = Path(source)
    folder_size_threshold_bytes = folder_size_threshold_gb * (1024 ** 3)
    temporary_folder = Path(temporary_folder)
    temporary_folder.mkdir(parents=True, exist_ok=True)

    # Check if temporary folder is a subdirectory of source
    if source in temporary_folder.parents:
        raise ValueError('Temporary folder cannot be a subdirectory of the source folder.')

    # Check if temporary folder only contains what was supposedly previous backup files (i.e. *.txt, *.tar, and *.tar.gz)
    for file in temporary_folder.iterdir():
        if file.is_file():
            if file.suffix in ['.txt', '.tar', '.gz']:
                continue
            if file.name == '.DS_Store':
                continue

        raise ValueError(f'{str(file)} might not be a previous backup file. Exiting.')

    # Then remove all the files in the temporary folder
    shutil.rmtree(temporary_folder)
    temporary_folder.mkdir(parents=True, exist_ok=True)

    def _create_archive(folder_index, folder_size, folder_directories):
        # Create a tar file for the current folder
        if compress:
            tar_file = temporary_folder / f'{folder_index}.tar.gz'
        else:
            tar_file = temporary_folder / f'{folder_index}.tar'

        if compress:
            if use_absolute_paths_in_archive:
                subprocess.check_output(['tar', '-czf', tar_file, *folder_directories])
            else:
                subprocess.check_output(['tar', '-czf', tar_file, '-C', str(source), *folder_directories])
        else:
            if use_absolute_paths_in_archive:
                subprocess.check_output(['tar', '-cf', tar_file, *folder_directories])
            else:
                subprocess.check_output(['tar', '-cf', tar_file, '-C', str(source), *folder_directories])

        # Write list of folders in this tar file to a text file
        with open(tar_file.with_suffix('.txt'), 'w') as f:
            f.write('\n'.join(folder_directories))

        print(f'Created tar file {tar_file}. Content size: {folder_size / (1024 ** 3)} GB. Output size: {tar_file.stat().st_size / (1024 ** 3)} GB.')


    # Iteratively add folders to the tar file
    current_folder_index = 0
    current_folder_size = 0
    current_folder_directories = []

    for folder in source.iterdir():
        if use_absolute_paths_in_archive:
            folder_name = folder
        else:
            folder_name = folder.name

        current_folder_size += du(folder)
        current_folder_directories.append(str(folder_name))

        if current_folder_size > folder_size_threshold_bytes:
            _create_archive(current_folder_index, current_folder_size, current_folder_directories)

            # Increment the index
            current_folder_index += 1
            current_folder_size = 0
            current_folder_directories = []

    # Create the last tar file
    if current_folder_directories:
        _create_archive(current_folder_index, current_folder_size, current_folder_directories)


# Print output as executing https://stackoverflow.com/a/4417735/10538006
def execute(cmd):
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            print(line, end='')

def upload_archives(temporary_folder, destination):
    """Uses rclone to upload all the files in the temporary folder to the destination."""
    execute(['rclone', 'copy', str(temporary_folder), destination, '--progress'])

def update_archives(temporary_folder, base_destination_folder, number_to_keep):
    """Deletes the oldest archives in the base destination folder to keep only the latest `number_to_keep` archives."""
    if not base_destination_folder.endswith('/'):
        raise Exception('Base destination folder must end with a slash.')

    s = subprocess.check_output(['rclone', 'lsd', base_destination_folder])
    folders = [line.split()[-1] for line in s.decode('utf-8').split('\n') if line]
    print('Folders in destination base:', *folders)

    try:
        folders = [int(f) for f in folders]
    except ValueError:
        raise Exception('Folders in the destination base must be integers.')

    if len(folders) > number_to_keep - 1:
        folders.sort()
        folders_to_delete = folders[:-(number_to_keep - 1)]
        print('Deleting destination folders:', *folders_to_delete)
        for folder in folders_to_delete:
            print('rclone', 'purge', base_destination_folder + str(folder) + '/')
            execute(['rclone', 'purge', base_destination_folder + str(folder) + '/'])

    upload_archives(temporary_folder, base_destination_folder + str(int(time.time())) + '/')

# if __name__ == '__main__':
#     # Test parameters -- just back up a small folder
#     source = '/Users/longyuxi/Documents/Duke/'
#     folder_size_threshold_gb = 0.000001  # Create a new tar file for each subfolder
#     temporary_folder = '/Users/longyuxi/Downloads/backuptemp/'
#     base_destination_folder = 'onedrive:backup/mac/test/'

#     make_archives(source, folder_size_threshold_gb, temporary_folder)
#     time.sleep(5)
#     update_archives(temporary_folder, base_destination_folder, 3)

