#!/usr/bin/env python

# Copyright 2014 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import distutils.spawn
import errno
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

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


def get_cwd(process):
    """ Get the cwd of a process catching 
    AccessDenied exceptions """
    try:
        cwd =  process.getcwd()
    except:
        cwd = 'AccessDenied'
    return cwd


def detect_package_via_call_tree(call_tree):
    """ Heuristic to detect a package if called via catkin_make_isolated """
    for p in call_tree:
        for arg in p['commandline']:
            if 'cmi_env.py' in arg:
                # Get the name of the directory before cmi_env.py
                return os.path.basename(os.path.dirname(arg))

    return None

class CallTree:
    def __init__(self, results):
        self.results = results

    def __enter__(self):
        p = psutil.Process(os.getpid())
        self.results['call_tree'] = self.call_tree(p)
        self.results['cwd'] = get_cwd(p)

        # heuristic to detect building package
        self.results['package'] = detect_package_via_call_tree(self.results['call_tree'])

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
        info['cwd'] = get_cwd(process)
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


def verify_directory(directory):
    # like makedir -p
    if os.path.isdir(directory):
        return
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno == errno.EEXISST and os.path.isdir(directory):
            pass
        else:
            raise e


def generate_results_yaml(results):
    yaml_content = ''
    for k, v in results.items():
        yaml_content += '%s: %s\n' % (k, v)
    return yaml_content


def record_results(results, directory):
    verify_directory(directory)
    filename = os.path.join(directory, 
                            os.path.basename(results['command'][0]) + 
                            '_' + ('%4f' % results['start_time']) + '.yaml')
    #yaml_results =  generate_results_yaml(results)
    yaml_results = yaml.safe_dump(results, default_flow_style=False)
    debug(">>>> Writing results to file %s" % filename)
    with open(filename, 'w') as fh:
        fh.write(yaml_results)

def get_results_directory():
    return os.getenv('WATCHPROCESS_RESULTS_DIRECTORY', '/tmp/watchprocess')

def get_results_files(results_dir):
    return [ os.path.join(results_dir, f) for f in os.listdir(results_dir) if f.endswith('.yaml')]
    



def indirection_main(alternate_argv0 = None):

    args = sys.argv

    if alternate_argv0:
        args[0] = alternate_argv0

    config = {}
    results = {}
    context_managers = []

    context_managers.append(Timer(results))
    context_managers.append(Resources(results))
    context_managers.append(CallTree(results))


    new_args, new_env = rewrite_args_for_monitoring(args)
    debug(">>>>Watchprocess Running %s on path %s" % (args, os.getenv('PATH')))
    debug(">>>>Watchprocess Substituting %s on path %s" % (new_args, new_env['PATH']))

    with nested(*context_managers):

        retcode = subprocess.call(new_args, env=new_env)
        results['returncode'] = retcode
        results['command'] = new_args

    debug(">>>>Watchprocess Results:")
    debug(generate_results_yaml(results))
    debug(">>>>End Watchprocess Results:")


    output_dir = get_results_directory()
    record_results(results, output_dir)


    sys.exit(retcode)


def standard_main():
    #defered loading for speed
    import argparse
    
    parser = argparse.ArgumentParser(description='Process monitoring application')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False)

    subparsers = parser.add_subparsers(help='subcommands of watchprocess')
    cleanparser = subparsers.add_parser('clean')
    cleanparser.add_argument('-y', action='store_true', default=False, 
                             dest='yes', help="Do not propt user for confirmation")
    cleanparser.set_defaults(func=clean_main)


    collectparser = subparsers.add_parser('collect')
    collectparser.add_argument('-y', action='store_true', default=False, 
                             dest='yes', help="Do not propt user for confirmation")
    collectparser.add_argument('--csv', action='store_true', default=False, 
                             dest='csv', help="Output format csv")
    collectparser.add_argument('--output-filename', '-O', action='store', default=None, 
                             dest='output_file', help="Output filename, default stdout")
    collectparser.add_argument('--filter-greater-than', action='append', nargs=2, default=None,
                               help='(field_name, max_value) to filter results', dest='filters')
    collectparser.set_defaults(func=collect_main)

    args = parser.parse_args()
    args.func(args)

    sys.exit(0)



def clean_main(args):
    results_dir = get_results_directory()
    filelist = get_results_files(results_dir)
    
    print("Running clean subcommand")
    if not args.yes:
        input_val = raw_input("Do you want to remove these files:\n %s \n Press y to remove these %s files:" % (filelist, len(filelist)))
        if input_val != 'y':
            print("you did not press y, I will not remove those files")
            return
    for f in filelist:
        os.remove(f)
    print("Removed %s files from %s" % (len(filelist), results_dir))




def csv_export(collected_results):

    element_names = ['returncode', 'start_time', 'finish_time', 'elapsed_time', 'major_page_fault', 'user_cpu', 'system_cpu', 'resident_memory_size', 'package']

    def results_entry(result):
        
        values = []
        values.append(' '.join(result['command']))
        for e in element_names:
            if e in result:
                values.append(str(result[e]))
            else:
                values.append(' ')
        return ', '.join(values)

    lines = []
    legend = '#' + ', '.join(['command'] + element_names)
    lines.append(legend)
    for result in collected_results:
        lines.append(results_entry(result))
    

    return '\n'.join(lines)

def filter_match(results, filters):
    """ Return true if the results match the filters"""
    for f in filters:
        if f[0] in results:
            if results[f[0]] > float(f[1]):
                return True
    return False

def collect_main(args):
    # Deferred loading for speed
    import yaml
    results_dir = get_results_directory()
    filelist = get_results_files(results_dir)
    collected_results = []
    for f in filelist:
        try:
            with open(f, 'r') as fh:
                y = yaml.load(fh.read())
                if args.filters:
                    if filter_match(y, args.filters):
                        collected_results.append(y)
                else:
                    collected_results.append(y)
        except Exception as ex:
            print("Failed to load %s, skipping. The errors was: %s" % (f, ex))

    if args.csv:
        output = csv_export(collected_results)
    else:
        output = yaml.dump(collected_results, default_flow_style=False)

    if args.output_file:
        with open(args.output_file, 'w') as fh:
            fh.write(output)
    else:
        print(output)

if __name__ == '__main__':
    if os.path.basename(sys.argv[0]) != 'watchprocess.py':
        indirection_main()
    standard_main()
