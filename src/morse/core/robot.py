import logging; logger = logging.getLogger("morse." + __name__)
from abc import ABCMeta
import morse.core.object
from morse.core import blenderapi
from morse.helpers.components import add_property

class Robot(morse.core.object.Object):
    """ Basic Class for all robots

    Inherits from the base object class.
    """

    add_property('_free_z', False, 'FreeZ', 'bool',
                'Indicate if Z is really a freedom degree of the robot, \
                i.e. basically if it is a flying or submarine robot')

    # Make this an abstract class
    __metaclass__ = ABCMeta

    def __init__ (self, obj, parent=None):
        """ Constructor method. """
        # Call the constructor of the parent class
        super(Robot, self).__init__(obj, parent)
        
        # Add the variable move_status to the object
        self.move_status = "Stop"

        # shift against the simulator time (in ms)
        self.time_shift = 0.0

        self.is_dynamic = bool(self.bge_object.getPhysicsId())

    def action(self):
        """ Call the regular action function of the component. """
        # Update the component's position in the world
        self.position_3d.update(self.bge_object)

        self.default_action()

    def gettime(self):
        """ Return the current time, as seen by the robot, in milli seconds """
        return blenderapi.persistantstorage().current_time * 1000.0 +\
               self.time_shift

    def apply_speed(self, kind, linear_speed, angular_speed):
        """
        Apply speed parameter to the robot

        :param string kind: the kind of control to apply. Can be one of
        ['Position', 'Velocity'].
        :param list linear_speed: the list of linear speed to apply, for
        each axis, in m/s.
        :param list angular_speed: the list of angular speed to apply,
        for each axis, in rad/s.
        """

        parent = self.bge_object
        must_fight_against_gravity = self.is_dynamic and self._free_z

        if must_fight_against_gravity:
            parent.applyForce(-blenderapi.gravity())

        if kind == 'Position':
            if must_fight_against_gravity:
                parent.worldLinearVelocity = [0.0, 0.0, 0.0]
            parent.applyMovement(linear_speed, True)
            parent.applyRotation(angular_speed, True)
        elif kind == 'Velocity':
            parent.setLinearVelocity(linear_speed, True)
            parent.setAngularVelocity(angular_speed, True)
