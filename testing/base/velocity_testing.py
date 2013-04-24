#! /usr/bin/env python
"""
This script tests some of the base functionalities of MORSE.
"""

import sys
from time import sleep
from morse.testing.testing import MorseTestCase
from pymorse import Morse

# Include this import to be able to use your test file as a regular 
# builder script, ie, usable with: 'morse [run|exec] base_testing.py
try:
    from morse.builder import *
except ImportError:
    pass

def send_speed(s, v, w):
    s.publish({'v' : v, 'w' : w})

class Velocity_Test(MorseTestCase):
    def setUpEnv(self):
        """ Defines the test scenario, using the Builder API.
        """
        robot = ATRV()

        motion = MotionVW()
        robot.append(motion)
        motion.add_stream('socket')

        vel = Velocity()
        robot.append(vel)
        vel.add_stream('socket')
        
        env = Environment('empty', fastmode = True)
        env.add_service('socket')

    def test_vw_controller(self):
        with Morse() as simu:
            precision=0.05
        
            vel_stream = simu.robot.vel
            v_w = simu.robot.motion

            # Read the initial speed
            vel = vel_stream.get()
            self.assertAlmostEquals(vel['linear_velocity'][0], 0.0, delta=precision)
            self.assertAlmostEquals(vel['linear_velocity'][1], 0.0, delta=precision)
            self.assertAlmostEquals(vel['linear_velocity'][2], 0.0, delta=precision)
            self.assertAlmostEquals(vel['angular_velocity'][0], 0.0, delta=precision)
            self.assertAlmostEquals(vel['angular_velocity'][1], 0.0, delta=precision)
            self.assertAlmostEquals(vel['angular_velocity'][2], 0.0, delta=precision)
            self.assertAlmostEquals(vel['world_linear_velocity'][0], 0.0, delta=precision)
            self.assertAlmostEquals(vel['world_linear_velocity'][1], 0.0, delta=precision)
            self.assertAlmostEquals(vel['world_linear_velocity'][2], 0.0, delta=precision)

            send_speed(v_w, 1.0, 0.0)
            sleep(0.5)

            vel = vel_stream.get()
            print(vel)

            vel = vel_stream.get()
            self.assertAlmostEquals(vel['linear_velocity'][0], 1.0, delta=precision)
            self.assertAlmostEquals(vel['linear_velocity'][1], 0.0, delta=precision)
            self.assertAlmostEquals(vel['linear_velocity'][2], 0.0, delta=precision)
            self.assertAlmostEquals(vel['angular_velocity'][0], 0.0, delta=precision)
            self.assertAlmostEquals(vel['angular_velocity'][1], 0.0, delta=precision)
            self.assertAlmostEquals(vel['angular_velocity'][2], 0.0, delta=precision)
            self.assertAlmostEquals(vel['world_linear_velocity'][0], 1.0, delta=precision)
            self.assertAlmostEquals(vel['world_linear_velocity'][1], 0.0, delta=precision)
            self.assertAlmostEquals(vel['world_linear_velocity'][2], 0.0, delta=precision)


########################## Run these tests ##########################
if __name__ == "__main__":
    import unittest
    from morse.testing.testing import MorseTestRunner
    suite = unittest.TestLoader().loadTestsFromTestCase(Velocity_Test)
    sys.exit(not MorseTestRunner().run(suite).wasSuccessful())

