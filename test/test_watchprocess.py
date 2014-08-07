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

import os
import subprocess
import unittest

class TestSymlink(unittest.TestCase):

    def debug_env(self):
        env = os.environ.copy()
        env['WATCHPROCESS_DEBUG'] = '1'
        return env

    def check_for_gcc_usage(self, console_output):
        self.assertTrue("Usage: gcc [options] file..." in console_output, "gcc did not generate usage")

    def check_for_watchprocess_debug(self, console_output):
        self.assertTrue("Watchprocess" in console_output, "Did not catch Watchprocess indirection.")

    def check_for_no_watchprocess_debug(self, console_output):
        self.assertFalse("Watchprocess" in console_output, "Improperly found Watchprocess indirection.")

    def test_explicit_execution(self):
        try:
            output = subprocess.check_output(['./test/symlinks/gcc', '--help'], env=self.debug_env())
            self.check_for_watchprocess_debug(output)
            self.check_for_gcc_usage(output)
        except subprocess.CalledProcessError as ex:
            self.assertFalse("Should not get here", "Invalid exception %s" % ex)


    def test_path_extension_execution(self):
        new_env = self.debug_env()
        new_env["PATH"] = ':'.join([os.path.abspath('./test/symlinks'), new_env['PATH']])
        try:
            output =subprocess.check_output(['gcc', '--help'], env=new_env)
            self.check_for_watchprocess_debug(output)
            self.check_for_gcc_usage(output)
        except subprocess.CalledProcessError as ex:
            self.assertFalse("Should not get here", "Invalid exception %s" % ex)


    def test_debug_suppression(self):
        try:
            output = subprocess.check_output(['./test/symlinks/gcc', '--help'])
            self.check_for_no_watchprocess_debug(output)
            self.check_for_gcc_usage(output)
        except subprocess.CalledProcessError as ex:
            self.assertFalse("Should not get here", "Invalid exception %s" % ex)
