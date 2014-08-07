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


# This will not be executed by default by nose tests and its output is to the screen. To run it use:

# `nosetests -s test/performance.py` 

# and look at the console for the results. 

import os
import subprocess
import unittest
import time

class TestPerformance(unittest.TestCase):

    def debug_env(self):
        env = os.environ.copy()
        env['WATCHPROCESS_DEBUG'] = '1'
        return env

    def run_gcc(self):
        try:
            output = subprocess.check_output(['/usr/bin/gcc', '--help'], env=self.debug_env())
        except subprocess.CalledProcessError as ex:
            self.assertFalse("Should not get here", "Invalid exception %s" % ex)

    def run_explicit_execution(self):
        try:
            output = subprocess.check_output(['./test/symlinks/gcc', '--help'], env=self.debug_env())
        except subprocess.CalledProcessError as ex:
            self.assertFalse("Should not get here", "Invalid exception %s" % ex)

    def test_performance(self):
        loops = 100
        basic_start_time = time.time()
        for i in range(loops):
            self.run_gcc()
        basic_finish_time = time.time()
        basic_mean_time = (basic_finish_time - basic_start_time) / loops

        instrumented_start_time = time.time()
        for i in range(loops):
            self.run_explicit_execution()
        instrumented_finish_time = time.time()
        instrumented_mean_time = (instrumented_finish_time - instrumented_start_time) / loops
        
        print("basic: %s %s (%s) = %s" % (basic_start_time, basic_finish_time,
                                          loops, basic_mean_time))


        print("instrumented: %s %s (%s) = %s" % (instrumented_start_time, instrumented_finish_time,
                                          loops, instrumented_mean_time))

        overhead = (instrumented_mean_time - basic_mean_time)
        print("overhead per call: %s" % overhead)

        self.assertTrue(overhead < 0.100, "Overhead too high")
