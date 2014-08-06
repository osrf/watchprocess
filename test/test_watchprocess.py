#!/usr/bin/env python

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
