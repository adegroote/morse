"""
This module deals with the time management in Morse, providing several
possible implementations.

At the moment, it provides two implementations:
    - best effort (i.e. try to simulate at real-time, by dropping
      frame). The simulation is less acurate, because the physical steps
      are not really constant.
    - fixed simulation step. Compute all physical / logical step. The
      simulation will be more precise, but the simulation time will
      differ from computer clock time.
"""

import logging
logger = logging.getLogger("morse." + __name__)
import time
from morse.core import blenderapi
from morse.helpers.statistics import Stats

import socket
import select

class BestEffortStrategy:
    def __init__ (self):
        self.time = time.time()

        self._stat_jitter = Stats()
        self._stat_nb_frame = Stats()
        self._time_frame = 0.0
        self._last_time = 0.0
        self._nb_frame = 0

        logger.info('Morse configured in Best Effort Mode')

    def update (self):
        self.time = time.time()
        self._update_statistics()

    def name(self):
        return 'Best Effort'
    
    @property
    def mean(self):
        return self._stat_jitter.mean

    def statistics(self):
        return {
            "mean_time" : self._stat_jitter.mean,
            "variance_time": self._stat_jitter.variance,
            "mean_frame_by_sec": self._stat_nb_frame.mean,
            "variance_frame_by_sec": self._stat_nb_frame.variance
        }

    def _update_statistics(self):
        if self._last_time == 0.0:
            self._last_time = self.time
        else:
            ds = self.time - self._last_time
            self._last_time = self.time
            self._stat_jitter.update(ds)

        if self._nb_frame == 0:
            self._time_frame = self.time
            self._nb_frame = 1
        else:
            if self.time - self._time_frame > 1.0:
                self._stat_nb_frame.update(self._nb_frame)
                self._nb_frame = 0
            else:
                self._nb_frame = self._nb_frame + 1

class FixedSimulationStepStrategy:
    def __init__ (self):
        self.time = time.time()
        self._incr = 1.0 / blenderapi.getfrequency()

        self._stat_jitter = Stats()
        self._last_time = 0.0

        logger.info('Morse configured in Fixed Simulation Step Mode with '
                    'time step of %f sec ( 1.0 /  %d)' %
                    (self._incr, blenderapi.getfrequency()))

    def update (self):
        self.time = self.time + self._incr
        self._update_statistics()

    def name (self):
        return 'Fixed Simulation Step'

    @property
    def mean(self):
        return self._incr

    def statistics (self):
        return {
            "mean_time" : self._stat_jitter.mean,
            "variance_time": self._stat_jitter.variance,
            "diff_real_time": self.time - time.time()
        }

    def _update_statistics(self):
        if self._last_time == 0.0:
            self._last_time = time.time()
        else:
            ds = time.time() - self._last_time
            self._last_time = time.time()
            self._stat_jitter.update(ds)

class FixedSimulationStepExternalTriggerStrategy(FixedSimulationStepStrategy):
    SYNC_PORT = 5000

    def __init__(self):
        FixedSimulationStepStrategy.__init__(self)
        self._init_trigger()

    def _init_trigger(self):
        self._client =  None
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(('', self.SYNC_PORT))
        self._server.listen(1)

    def _wait_trigger(self):
        # If there is some client, just wait on it
        if self._client:
            logger.debug("Waiting trigger")
            msg = self._client.recv(2048)
            if not msg: #deconnection of client
                self._client = None
        else:
        # Otherwise, we just check if there is some client waiting
        # If there is no client, we do not block for the moment to avoid
        # weird interaction at the startup
            try:
                inputready, _, _ = select.select([self._server], [], [], 0)
            except select.error:
                pass
            except socket.error:
                pass

            if self._server in inputready:
                self._client, _ = self._server.accept()

    def _end_trigger(self):
        self._client.close()
        self._server.shutdown(socket.SHUT_RDWR)

    def __del__(self):
        self._end_trigger()

    def update(self):
        self._wait_trigger()
        FixedSimulationStepStrategy.update(self)

    def name(self):
        return 'Fixed Simulation Step with external trigger'

class TimeStrategies:
    (BestEffort, FixedSimulationStep, FixedSimulationStepExternalTrigger) = range(3)

    internal_mapping = {
        BestEffort:
            { "impl": BestEffortStrategy,
              "python_repr": b"TimeStrategies.BestEffort",
              "human_repr" : "Best Effort"
            },
        FixedSimulationStep:
            { "impl": FixedSimulationStepStrategy,
              "python_repr": b"TimeStrategies.FixedSimulationStep",
              "human_repr": "Fixed Simulation Step"
            },
        FixedSimulationStepExternalTrigger:
            { "impl": FixedSimulationStepExternalTriggerStrategy,
              "python_repr": b"TimeStrategies.FixedSimulationStepExternalTrigger",
              "human_repr": "Fixed Simulation Step with an external trigger"
            }
        }

    @staticmethod
    def make(strategy):
        try:
            return TimeStrategies.internal_mapping[strategy]["impl"]()
        except KeyError:
            return None
    @staticmethod
    def python_repr(strategy):
        try:
            return TimeStrategies.internal_mapping[strategy]["python_repr"]
        except KeyError:
            return None

    @staticmethod
    def human_repr(strategy):
        try:
            return TimeStrategies.internal_mapping[strategy]["human_repr"]
        except KeyError:
            return None


def time_isafter(t1, t2):
    """ Returns true if t1 > t2 in morse_time. Returns false otherwise """
    return t2 - t1 < blenderapi.persistantstorage().time.mean / 2
