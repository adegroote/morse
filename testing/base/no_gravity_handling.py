#! /usr/bin/env python
"""
This script tests the waypoints actuator, both the data and service api
"""

import sys
from morse.testing.testing import MorseTestCase
from pymorse import Morse

# Include this import to be able to use your test file as a regular 
# builder script, ie, usable with: 'morse [run|exec] base_testing.py
try:
    from morse.builder import *
except ImportError:
    pass

class NoGravityHandlings_Test(MorseTestCase):
    def setUpEnv(self):
        """ Defines the test scenario, using the Builder API.
        """
        robot = Quadrotor()
        robot.properties(NoGravity = True)
        robot.translate(x = 0.0, y = 0.0, z = 5.0)

        pose = Pose()
        robot.append(pose)
        pose.add_stream('socket')

        kb = Keyboard()
        kb.properties(ControlType = 'Velocity')
        robot.append(kb)

        env = Environment('empty', fastmode = True)
        env.add_service('socket')

    def test_(self):
        """ This test is guaranteed to be started only when the simulator
        is ready.
        """
        with Morse() as morse:
        
            pose_stream = morse.robot.pose
            pose = pose_stream.get()
            self.assertAlmostEqual(pose['x'],  0.0, delta = 0.01)
            self.assertAlmostEqual(pose['y'], 0.0, delta = 0.01)
            self.assertAlmostEqual(pose['z'], 5.0, delta = 0.01)

            morse.sleep(2)

            pose = pose_stream.get()
            self.assertAlmostEqual(pose['x'],  0.0, delta = 0.01)
            self.assertAlmostEqual(pose['y'], 0.0, delta = 0.01)
            self.assertAlmostEqual(pose['z'], 5.0, delta = 0.01)



########################## Run these tests ##########################
if __name__ == "__main__":
    from morse.testing.testing import main
    main(NoGravityHandlings_Test)
