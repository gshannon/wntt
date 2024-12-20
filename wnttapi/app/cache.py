from os import access, R_OK, remove
from os.path import isfile
import pickle
import logging
from django.conf import settings


"""Implement a bare bones pickle cache"""


logger = logging.getLogger(__name__)


def file_exists(filename):
    path = to_path(filename)
    return isfile(path) and access(path, R_OK)


def delete_file(filename):
    path = to_path(filename)
    logger.info(f'deleting {path}')
    try:
        remove(path)
    except FileNotFoundError:
        pass
    return


def write_to_cache(filename, data):
    path = to_path(filename)
    logger.debug(f'writing to {path}')
    pred_file = open(path, 'wb')
    pickle.dump(data, pred_file)
    pred_file.close()


def read_from_cache(filename):
    path = to_path(filename)
    logger.debug(f'reading from {path}')
    file = open(path, 'rb')
    data = pickle.load(file)
    file.close()
    return data


def to_path(filename):
    return settings.BASE_DIR / 'cache' / filename
