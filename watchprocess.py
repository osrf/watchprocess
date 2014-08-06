#!/usr/bin/env python

import copy
import distutils.spawn
import os
import shutil
import subprocess
import sys
import tempfile

# Known deprecated but no alternative with python 2 compatability. 
from contextlib import nested


# Timer
import time

# Resources
import resource

#CallTree
import psutil

class MonitorError(Exception):
    """ Base class for exceptions"""
    pass

class PathError(MonitorError):
    pass


def debug(args):
    if os.getenv('WATCHPROCESS_DEBUG', '0') in ['1', 'True', 'true']:
        print(args)

def basename_equal(path1, path2):
    return os.path.basename(path1) == os.path.basename(path2)



class Timer:

    def __init__(self, results, max=None):
        self.timeout = max
        self.results = results
    def __enter__(self):
        self.start_time = time.time()
    def __exit__(self, type, error, traceback):
        finish_time = time.time()
        elapsed_time = (finish_time - self.start_time)
        self.results['start_time'] = self.start_time
        self.results['finish_time'] = finish_time
        self.results['elapsed_time'] = elapsed_time



class Resources:
    def __init__(self, results):
        self.results = results
        
    def __enter__(self):
        pass
    def __exit__(self, type, error, traceback):
        try:
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        except resource.error as e:
            print("Failed to get resource usage. Data will not be reported")
            return
        self.results['user_cpu'] = usage.ru_utime
        self.results['system_cpu'] = usage.ru_stime
        self.results['resident_memory_size'] = usage.ru_maxrss
        # not in linux self.results['shared_memory_size'] = usage.ru_ixrss
        # not in linux self.results['unshared_memory_size'] = usage.ru_idrss
        # not in linux self.results['unshared_stack_size'] = usage.ru_isrss
        self.results['minor_page_fault'] = usage.ru_minflt
        self.results['major_page_fault'] = usage.ru_majflt
        self.results['swap_outs'] = usage.ru_nswap
        self.results['block_inputs'] = usage.ru_inblock
        self.results['block_outputs'] = usage.ru_oublock
        self.results['voluntary_context_switches'] = usage.ru_nvcsw
        self.results['involuntary_context_switches'] = usage.ru_nivcsw






class CallTree:
    def __init__(self, results):
        self.results = results

    def __enter__(self):
        p = psutil.Process(os.getpid())
        self.results['call_tree'] = self.call_tree(p)
        
    def __exit__(self, type, error, traceback):
        pass

    def call_tree(self, process):
        parent = process.parent
        if parent:
            extension = self.call_tree(parent)
        else:
            extension = []
        return extension + [self.process_info(process)] 

    def process_info(self, process):
        info = {}
        info['name'] = process.name
        info['pid'] = process.pid
        info['commandline'] = process.cmdline
        return info


class AlternateCwd:
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tempdir)
        return self
        
    def __exit__(self, type, error, traceback):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tempdir)


    def find_executable(self, arg, path):
        """ This class changes the cwd to an emptry directory to avoid
        infinite loops"""
        return distutils.spawn.find_executable(arg, path)

def detect_next_path_instance(argv0, path):
    """ This will take an executable name and path and find the next
    instance of that executable on the path to return. 
    
    Raises PathError if second location cannot be found. """
    path_list = path.split(os.pathsep)
    basename = os.path.basename(argv0)
    initial_version = os.path.abspath(argv0)
    next_version = initial_version 

    with AlternateCwd() as acwd:
        while(len(path_list) >= 1):
            next_version = acwd.find_executable(basename, os.pathsep.join(path_list))
            debug("found %s in %s" % (next_version, os.pathsep.join(path_list)))
            if next_version is None:
                raise PathError("Second version of %s not found on path %s" % (argv0, path_list))
            if next_version != initial_version:
                break
            path_list.pop(0)

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

config = {}
results = {}
context_managers = []

context_managers.append(Timer(results))
context_managers.append(Resources(results))
context_managers.append(CallTree(results))


new_args, new_env = rewrite_args_for_monitoring(sys.argv)
debug(">>>>Watchprocess Running %s on path %s" % (sys.argv, os.getenv('PATH')))
debug(">>>>Watchprocess Substituting %s on path %s" % (new_args, new_env['PATH']))

with nested(*context_managers):

    retcode = subprocess.call(new_args, env=new_env)
    results['returncode'] = retcode
    results['command'] = new_args

debug(">>>>Watchprocess Results:")
for k, v in results.items():
    debug(">>>> %s: %s" % (k, v))

sys.exit(retcode)
