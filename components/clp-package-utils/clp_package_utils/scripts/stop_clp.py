import argparse
import logging
import pathlib
import subprocess
import sys

from clp_package_utils.general import (
    CLP_DEFAULT_CONFIG_FILE_RELATIVE_PATH,
    container_exists,
    get_clp_home,
    is_container_running,
    validate_and_load_compression_queue_credentials_file,
    validate_and_load_config_file,
    validate_and_load_db_credentials_file
)
from clp_py_utils.clp_config import (
    DB_COMPONENT_NAME,
    COMPRESSION_QUEUE_COMPONENT_NAME,
    RESULTS_CACHE_COMPONENT_NAME,
    SEARCH_QUEUE_COMPONENT_NAME,
    SEARCH_SCHEDULER_COMPONENT_NAME,
    SEARCH_WORKER_COMPONENT_NAME,
    COMPRESSION_WORKER_COMPONENT_NAME,
    COMPRESSION_JOB_HANDLER_COMPONENT_NAME,
    WEBUI_COMPONENT_NAME,
    WEBUI_QUERY_HANDLER_COMPONENT_NAME,
)

# Setup logging
# Create logger
logger = logging.getLogger('clp')
logger.setLevel(logging.INFO)
# Setup console logging
logging_console_handler = logging.StreamHandler()
logging_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logging_console_handler.setFormatter(logging_formatter)
logger.addHandler(logging_console_handler)


def stop_container(container_name: str, stale_containers: list):
    if is_container_running(container_name):
        logger.info(f"Stopping {container_name}...")
        cmd = ['docker', 'stop', container_name]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, check=True)

        logger.info(f"Removing {container_name}...")
        cmd = ['docker', 'rm', container_name]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, check=True)
        logger.info(f"Stopped and Removed {container_name}.")
    elif container_exists(container_name):
        stale_containers.append(container_name)


def stop_queue_container(component_name: str, instance_id: str, logs_dir: pathlib.Path, stale_containers: list):
    container_name = f'clp-{component_name}-{instance_id}'
    stop_container(container_name, stale_containers)

    queue_config_file_path = logs_dir / component_name / f'{container_name}.conf'
    if queue_config_file_path.exists():
        queue_config_file_path.unlink()


def main(argv):
    clp_home = get_clp_home()
    default_config_file_path = clp_home / CLP_DEFAULT_CONFIG_FILE_RELATIVE_PATH

    args_parser = argparse.ArgumentParser(description="Stops CLP")
    args_parser.add_argument('--config', '-c', default=str(default_config_file_path),
                             help="CLP package configuration file.")

    component_args_parser = args_parser.add_subparsers(dest='component_name')
    component_args_parser.add_parser(DB_COMPONENT_NAME)
    component_args_parser.add_parser(RESULTS_CACHE_COMPONENT_NAME)
    component_args_parser.add_parser(COMPRESSION_JOB_HANDLER_COMPONENT_NAME)
    component_args_parser.add_parser(COMPRESSION_QUEUE_COMPONENT_NAME)
    component_args_parser.add_parser(SEARCH_QUEUE_COMPONENT_NAME)
    component_args_parser.add_parser(SEARCH_SCHEDULER_COMPONENT_NAME)
    component_args_parser.add_parser(SEARCH_WORKER_COMPONENT_NAME)
    component_args_parser.add_parser(COMPRESSION_WORKER_COMPONENT_NAME)
    component_args_parser.add_parser(WEBUI_COMPONENT_NAME)
    component_args_parser.add_parser(WEBUI_QUERY_HANDLER_COMPONENT_NAME)

    parsed_args = args_parser.parse_args(argv[1:])

    if parsed_args.component_name:
        component_name = parsed_args.component_name
    else:
        component_name = ""

    # Validate and load config file
    try:
        config_file_path = pathlib.Path(parsed_args.config)
        clp_config = validate_and_load_config_file(config_file_path, default_config_file_path, clp_home)

        # Validate and load necessary credentials
        if component_name in ['', DB_COMPONENT_NAME]:
            validate_and_load_db_credentials_file(clp_config, clp_home, False)
        if component_name in ['', COMPRESSION_QUEUE_COMPONENT_NAME, SEARCH_QUEUE_COMPONENT_NAME,
                              COMPRESSION_WORKER_COMPONENT_NAME]:
            # TODO Validate the search queue credentials when the search queue is actually used
            validate_and_load_compression_queue_credentials_file(clp_config, clp_home, False)
    except:
        logger.exception("Failed to load config.")
        return -1

    try:
        # Read instance ID from file
        logs_dir = clp_config.logs_directory
        instance_id_file_path = logs_dir / 'instance-id'
        if not (logs_dir.exists() and logs_dir.is_dir() and instance_id_file_path.exists()):
            # No instance ID file, so nothing to do
            return 0
        with open(instance_id_file_path, 'r') as f:
            instance_id = f.readline()

        stale_containers = []

        if '' == component_name or WEBUI_COMPONENT_NAME == component_name:
            stop_container(f'clp-{WEBUI_COMPONENT_NAME}-{instance_id}', stale_containers)
        if '' == component_name or WEBUI_QUERY_HANDLER_COMPONENT_NAME == component_name:
            stop_container(f'clp-{WEBUI_QUERY_HANDLER_COMPONENT_NAME}-{instance_id}', stale_containers)
        if '' == component_name or COMPRESSION_WORKER_COMPONENT_NAME == component_name:
            stop_container(f'clp-{COMPRESSION_WORKER_COMPONENT_NAME}-{instance_id}', stale_containers)
        if '' == component_name or COMPRESSION_JOB_HANDLER_COMPONENT_NAME == component_name:
            container_name = f'clp-{COMPRESSION_JOB_HANDLER_COMPONENT_NAME}-{instance_id}'
            stop_container(container_name, stale_containers)
        if '' == component_name or SEARCH_WORKER_COMPONENT_NAME == component_name:
            stop_container(f'clp-{SEARCH_WORKER_COMPONENT_NAME}-{instance_id}', stale_containers)
        if '' == component_name or SEARCH_SCHEDULER_COMPONENT_NAME == component_name:
            container_name = f'clp-{SEARCH_SCHEDULER_COMPONENT_NAME}-{instance_id}'
            stop_container(container_name, stale_containers)

            container_config_file_path = logs_dir / f'{container_name}.yml'
            if container_config_file_path.exists():
                container_config_file_path.unlink()
        if '' == component_name or COMPRESSION_QUEUE_COMPONENT_NAME == component_name:
            stop_queue_container(COMPRESSION_QUEUE_COMPONENT_NAME, instance_id, logs_dir, stale_containers)
        if '' == component_name or SEARCH_QUEUE_COMPONENT_NAME == component_name:
            stop_queue_container(SEARCH_QUEUE_COMPONENT_NAME, instance_id, logs_dir, stale_containers)
        if '' == component_name or RESULTS_CACHE_COMPONENT_NAME == component_name:
            container_name = f'clp-{RESULTS_CACHE_COMPONENT_NAME}-{instance_id}'
            stop_container(container_name, stale_containers)
        if '' == component_name or DB_COMPONENT_NAME == component_name:
            stop_container(f'clp-{DB_COMPONENT_NAME}-{instance_id}', stale_containers)

        if '' == component_name:
            # NOTE: We can only remove the instance ID file if all containers have been stopped.
            # Currently, we only remove the instance file when all containers are stopped at once.
            # If a single container is stopped, it's expensive to check if the others are running,
            # so instead we don't remove the instance file. In the worst case, a user will have to
            # remove it manually.
            instance_id_file_path.unlink()

        if len(stale_containers) != 0:
            container_list = " ".join(stale_containers)
            logger.warning(f"The following containers potentially failed and were not removed: {container_list}")
            logger.warning(f"Run docker rm {container_list} to manually remove them")
    except:
        logger.exception("Failed to stop CLP.")
        return -1

    return 0


if '__main__' == __name__:
    sys.exit(main(sys.argv))