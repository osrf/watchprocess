#!/usr/bin/env python

import copy
from distutils.spawn import find_executable
import os
import subprocess
import sys
import tempfile


class MonitorError(Exception):
    """ Base class for exceptions"""
    pass

class PathError(MonitorError):
    pass



def basename_equal(path1, path2):
    return os.path.basename(path1) == os.path.basename(path2)


def detect_next_path_instance(argv0, path):
    """ This will take an executable name and path and find the next
    instance of that executable on the path to return. 
    
    Raises PathError if second location cannot be found. """
    path_list = path.split(os.pathsep)
    basename = os.path.basename(argv0)


    if len(path_list) < 2:
        raise PathError("Invalid path, too short for indirection: %s" % path)
    initial_version = os.path.abspath(argv0)
    next_version = initial_version 
    while(len(path_list) > 1):
        path_list.pop(0)
        next_version = find_executable(basename, os.pathsep.join(path_list))
        #print("found %s in %s" % (next_version, os.pathsep.join(path_list)))
        if next_version is None:
            raise PathError("Second version of %s not found on path %s" % (argv0, path_list))
        if next_version != initial_version:
            break

    if next_version == initial_version:
        raise PathError("Second version of %s not found on path after searching %s" % (argv0, path))
    return next_version, os.pathsep.join(path_list)


def rewrite_args_for_monitoring(args, path=None, env=None):
    if path is None:
        path = os.getenv('PATH')
    if env:
        new_env = copy.copy(env)
    else:
        new_env = os.environ.copy()
    next_version, shortented_path = detect_next_path_instance(args[0], path)
    new_args = args[:]
    new_args[0] = next_version
    new_env['PATH'] = shortented_path
    return new_args, new_env

new_args, new_env = rewrite_args_for_monitoring(sys.argv)
print(">>>>Watchprocess Running %s on path %s" % (sys.argv, os.getenv('PATH')))
print(">>>>Watchprocess Substituting %s on path %s" % (new_args, new_env['PATH']))
retcode = subprocess.call(new_args, env=new_env)


sys.exit(retcode)
