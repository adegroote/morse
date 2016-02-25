import logging; logger = logging.getLogger("morse." + __name__)
from abc import ABCMeta
import morse.core.robot
from morse.core import blenderapi
from morse.helpers.components import add_property
from morse.helpers.joints import Joint6DoF
import math

class PhysicsWheelRobot(morse.core.robot.Robot):
    """ Abstract base class for robots with wheels that turn as
        the robot moves.
        The wheels must be children of the robot in the Blender file.
        """
    # Make this an abstract class
    __metaclass__ = ABCMeta

    add_property('_has_suspension', True, 'HasSuspension', 'bool', 
                 'Determine if the underlaying robot has suspension, \
                  i.e. wheels can move independently of the body of the \
                  robot')

    # Local dictionaries to store references to the wheels
    _wheel_index = ['FL', 'FR', 'RL', 'RR']

    def __init__(self, obj, parent):
        morse.core.robot.Robot.__init__(self, obj, parent)
        self._wheels = {}
        self._wheel_joints = {}

    def get_wheels(self):
        """
        Get pointers to and physicsIds of all objects
        Compute wheel_radius too
        """
        scene = blenderapi.scene()

        self._wheel_radius = None

        caster_wheel_name = self.bge_object.get('CasterWheelName', None)

        #  inherited from the parent robot
        for index in self._wheel_index:
            name = "Wheel%sName" % index
            # Get the actual name of the object from the properties
            #  of the parent robot
            try:
                wheel = scene.objects[self.bge_object[name]]
                self._wheels[index] = wheel
                logger.info("\tWheel %s: %s" % (index, wheel.name))
                wheel.removeParent()

                # get wheel radius if not already computed
                if wheel.name != caster_wheel_name and not self._wheel_radius:
                    self._wheel_radius = self.get_wheel_radius(self.bge_object[name])
            except:
                pass

        logger.debug("get_wheels %s" % self._wheels)

    def get_track_width(self):
        vec = self._wheels['FL'].getVectTo(self._wheels['FR'])
        return vec[0]

    def get_distance_axle(self):
        vec = self._wheels['FL'].getVectTo(self._wheels['RL'])
        return vec[0]

    def get_wheel_radius(self, wheel_name):
        dims = blenderapi.objectdata(wheel_name).dimensions
        # average the x and y dimension to get diameter - divide by 2 for radius
        radius = (dims[0]+dims[1])/4
        return radius


class PhysicsDifferentialRobot(PhysicsWheelRobot):
    """
    Base class for mobile robots using a differential drive motion model.

    This base class handles the simulation of the physical interactions
    between differential-drive robots and the ground.
    """

    add_property('_fix_turning', 0.0, 'FixTurningSpeed', 'double', 
                'Overwrite the value of the distance between wheels in '
                'the computations of the wheel speeds. This effectively '
                'changes the turning speed of the robot, and can be used '
                'to compensate for the slip of the wheels while turning. '
                'If the value 0.0 is used, the real distance between wheels '
                'is used.')

    def __init__ (self, obj, parent=None):
        """ Constructor method. """
        # Call the constructor of the parent class
        PhysicsWheelRobot.__init__(self, obj, parent)

        # get wheel references and ID's
        self.get_wheels()

        # construct the vehicle
        self.build_vehicle()

        if self._fix_turning != 0.0:
            self._trackWidth = self._fix_turning

        logger.warn("Using wheel separation of %.4f" % self._trackWidth)

        # Force speed at 0.0 at startup
        self.apply_vw_wheels(0.0, 0.0)


    def build_vehicle(self):
        """ Apply the constraints to the vehicle parts. """

        # chassis ID - main object should be chassis model
        self._chassis_ID = self.bge_object.getPhysicsId()

        # get track width
        self._trackWidth = self.get_track_width()

        # set up wheel constraints
        # add wheels to either suspension arms or vehicle chassis
        if self._has_suspension:
            self.build_model_with_suspension()
        else:
            self.build_model_without_suspension()

    def build_model_without_suspension(self):
        """ Add all the constraints to attach the wheels to the body """
        for index in self._wheels.keys():
            self._wheel_joints[index] = Joint6DoF(self._wheels[index], self.bge_object)
            self._wheel_joints[index].free_rotation_dof('Z')

        # Add a free rotating wheel if indicated in the robot
        scene = blenderapi.scene()
        caster_wheel_name = self.bge_object.get('CasterWheelName', None)
        if caster_wheel_name and caster_wheel_name != 'None':
            wheel = scene.objects[caster_wheel_name]
            joint = Joint6DoF(wheel, self.bge_object)
            joint.free_rotation_dof('Z')

    def apply_vw_wheels(self, vx, vw):
        """ Apply (v, w) to the parent robot. """

        angle_control = 'Z'

        # calculate desired wheel speeds and set them
        if abs(vx) < 0.001 and abs(vw) < 0.001:
            # stop the wheel when velocity is below a given threshold
            for index in self._wheels.keys():
                self._wheel_joints[index].angular_velocity(angle_control, 0)

            self._stopped = True
        else:
            # this is need to "wake up" the physic objects if they have
            # gone to sleep apply a tiny impulse straight down on the
            # object
            if self._stopped:
                self.bge_object.applyImpulse(
                   self.bge_object.position, (0.0, 0.0, 0.000001))

            # no longer stopped
            self._stopped = False

            # Another formula for computing left and right wheel speeds:
            # http://www.uta.edu/utari/acs/jmireles/Robotics/KinematicsMobileRobots.pdf
            v_ws_l = vx - (self._trackWidth / 2.0) * vw
            v_ws_r = vx + (self._trackWidth / 2.0) * vw

            # convert to angular speeds
            w_ws_l =   -1.0 * v_ws_l / self._wheel_radius
            w_ws_r =   -1.0 * v_ws_r / self._wheel_radius

            # set wheel speeds - front and rear wheels have the same speed
            # Left side wheels
            self._wheel_joints['FL'].angular_velocity(angle_control, w_ws_l)
            if 'RL' in self._wheels:
                self._wheel_joints['RL'].angular_velocity(angle_control, w_ws_l)
            # Right side wheels
            self._wheel_joints['FR'].angular_velocity(angle_control, w_ws_r)
            if 'RR' in self._wheels:
                self._wheel_joints['RR'].angular_velocity(angle_control, w_ws_r)

            logger.debug("New speeds set: left=%.4f, right=%.4f" %
                         (w_ws_l, w_ws_r))

class PhysicsAckermannRobot(PhysicsWheelRobot):
    """
    Base class for mobile robots following the Ackermann steering principle

    This base class handles the simulation of the physical interactions
    between Ackermann-like vehicle and the ground.
    It assumes the vehicle has 4 wheels.
    """

    add_property('_max_steering_angle', 45.0, 'max_steering_angle', 'double', 
                 'The bigger angle possible the vehicle is able to turn \
                 its front wheel (in degree)')

    def __init__ (self, obj, parent=None):
        """ Constructor method. """
        # Call the constructor of the parent class
        PhysicsWheelRobot.__init__(self, obj, parent)

        # get wheel references and ID's
        self.get_wheels()

        self._max_steering_angle = math.radians(self._max_steering_angle)

        # construct the vehicle
        self.build_vehicle()

        self._axle_distance = self.get_distance_axle()

        logger.warn("Using wheel separation of %.4f" % self._trackWidth)

        # Force speed at 0.0 at startup
        self.apply_vw_wheels(0.0, 0.0)


    def build_vehicle(self):
        """ Apply the constraints to the vehicle parts. """
        # get track width
        self._trackWidth = self.get_track_width()

        # set up wheel constraints
        # add wheels to either suspension arms or vehicle chassis
        if self._has_suspension:
            self.build_model_with_suspension()
        else:
            self.build_model_without_suspension()

    def build_model_without_suspension(self):
        """ Add all the constraints to attach the wheels to the body """
        for index in ['FR', 'FL']:
            self._wheel_joints[index] = self.attach_front_wheel_to_body(
                    self._wheels[index], self.bge_object)
        for index in ['RR', 'RL']:
            self._wheel_joints[index] = self.attach_rear_wheel_to_body(
                    self._wheels[index], self.bge_object)

    def attach_front_wheel_to_body(self, wheel, parent):
        """ Attaches the wheel to the given parent using a 6DOF constraint

        Set the wheel positions relative to the robot in case the
        chassis was moved by the builder script or manually in blender
        """
        joint = Joint6DoF(wheel, parent)
        joint.limit_rotation_dof('Y', -self._max_steering_angle, self._max_steering_angle)
        joint.free_rotation_dof('Z')
        return joint # return a reference to the constraint


    def attach_rear_wheel_to_body(self, wheel, parent):
        """ Attaches the wheel to the given parent using a 6DOF constraint

        Set the wheel positions relative to the robot in case the
        chassis was moved by the builder script or manually in blender
        """
        joint = Joint6DoF(wheel, parent)
        joint.free_rotation_dof('Z')
        return joint # return a reference to the constraint

    def apply_vw_wheels(self, vx, vw):
        """ Apply (v, w) to the parent robot. """

        velocity_control = 'Z' 
        steering_control = 'Y'

        # calculate desired wheel speeds and set them
        if abs(vx) < 0.001 and abs(vw) < 0.001:
            # stop the wheel when velocity is below a given threshold
            for index in ['RL', 'RR']:
                self._wheel_joints[index].angular_velocity(velocity_control, 0)
            for index in ['FR', 'FL']:
                self._wheel_joints[index].angular_velocity(steering_control, 0)

            self._stopped = True
        else:
            # this is need to "wake up" the physic objects if they have
            # gone to sleep apply a tiny impulse straight down on the
            # object
            if self._stopped:
                self.bge_object.applyImpulse(
                   self.bge_object.position, (0.0, 0.0, 0.000001))

            # no longer stopped
            self._stopped = False

            # speed of rear wheels
            wx = -1.0 * vx / self._wheel_radius
            for index in ['RL', 'RR']:
                self._wheel_joints[index].angular_velocity(velocity_control, wx)

            logger.debug("Rear wheel speeds set to %.4f" % wx)

            # Compute angle of steering wheels
            if abs(vw) > 0.01:
                radius = vx / vw
                if abs(radius) < (self._trackWidth / 2):
                    l_angle = math.copysign(self._max_steering_angle, radius)
                    r_angle = math.copysign(self._max_steering_angle, radius)
                else:
                    cot_l_angle = self._axle_distance / (radius + (self._trackWidth / 2))
                    cot_r_angle = self._axle_distance / (radius -  (self._trackWidth / 2))
                    l_angle = math.atan(cot_l_angle)
                    r_angle = math.atan(cot_r_angle)
                    logger.debug('virtual angle %f' % (math.atan(self._axle_distance / radius)))
            else:
                l_angle = r_angle = 0.0

            logger.info("l_angle %f r_angle %f" % (l_angle, r_angle))

            if abs(l_angle) >= self._max_steering_angle or \
               abs(r_angle) >= self._max_steering_angle:
                logger.warning("Constraint (v = %f, w = %f) is not applicable \
                               due to physical limitation" % (vx, vw))

            current_l_angle = self._wheel_joints['FL'].euler_angle(steering_control)
            current_r_angle = self._wheel_joints['FR'].euler_angle(steering_control)

            diff_l_angle = l_angle - current_l_angle
            diff_r_angle = r_angle - current_r_angle

            self._wheel_joints['FL'].angular_velocity(steering_control, diff_l_angle)
            self._wheel_joints['FR'].angular_velocity(steering_control, diff_r_angle)

            logger.debug("Angle left w %f right w %f" % (diff_l_angle, diff_r_angle))


