"""
MIT License

Copyright (c) 2017 Roberto Sánchez Custodio. dev@r75.es

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from machine import Pin, Timer
import time

__version__ = '0.1.0'
__author__ = 'Roberto Sánchez'
__license__ = "MIT"

POLLING_PERIOD_MS = 200

class PIR():
    """
    A pythonic PIR (Passive Infrared Sensor) driver for micropython
    
    This driver control by software the sensor delay (but It should be greater than the delay defined in the own sensor),
    besides It add friendly API to add callback methods to be called when sensor detectes movement and when the movement is off

    References: 
    * http://www.instructables.com/id/PIR-Motion-Sensor-Tutorial/?ALLSTEPS
    * http://www.datasheet-pdf.info/entry/HC-SR501-Datasheet-PDF
    * https://learn.adafruit.com/pir-passive-infrared-proximity-motion-sensor/overview
    """

    def __init__(self, trigger_pin_id, reactivation_delay_ms=10000):
        self.trigger_pin = Pin(trigger_pin_id, mode=Pin.IN)
        self.active = False
        self._waiting_reactivation = False
        self.reactivation_delay = reactivation_delay_ms
        self._callback_on = None
        self._callback_off = None
        self._qtimer =  Timer(501) # 501 = timerID (from sensor model number)
        self._qtimer.init(period=200, mode=Timer.PERIODIC, callback=self._monitor)
        self._last_detection = None
    
    def _monitor(self, _=None):
        is_active_now = self.is_active(raw=True)
        if not self.active and is_active_now:
            # The sensor is active and the driver is not so we change the driver status to active
            self.active = True
            if self._callback_on: self._callback_on(self.trigger_pin)
            self._last_detection = time.ticks_ms()
            self._waiting_reactivation = False
        elif self.active:
            # The driver status is active,  the sensor can be active or not
            now = time.ticks_ms()
            if not is_active_now:
                # The sensor is not detecting movement but the driver keeps the active state
                # so we check if a new activation can happen again to reset the time to deactivation
                self._waiting_reactivation = True
            elif self._waiting_reactivation:
                # The sensor active again so we use this event as new time reference for deactivation
                self._last_detection = now
                self._waiting_reactivation = False

            if time.ticks_diff(now, self._last_detection) >= self.reactivation_delay:
                # the time from the last activation is greater than reactivation_delay
                # So we are ready to call end_callback or to keep the active status
                if is_active_now:
                    # We keep the active status a bit longer (self.reactivation_delay // 2)
                    self._last_detection = now - self.reactivation_delay // 2
                else:
                    # The sensor is not active and is time to deactivate the driver 
                    # and to call the end_callback is exists
                    self.active = False
                    self._waiting_reactivation = False
                    if self._callback_off: self._callback_off(self.trigger_pin)

    def clear(self):
        """
        Remove all registered callback methods
        """
        self._callback_on = None
        self._callback_off = None

    def init(self, trigger_pin_id, reactivation_delay_ms=10000):
        """
        Change the trigger pin and redefine the reactivation delay
        """
        self.trigger_pin = Pin(trigger_pin_id, mode=Pin.IN)
        self._prepare_monitor()
    
    def is_active(self, raw=False):
        """
        Return true if the sensor is currently detecting movement or if the time 
        from the last activation is less than the reactivation_delay.
        If raw==True then this method ignores the reactivation_delay and check the trigger pin
        """
        return bool(self.trigger_pin()) if raw else self.active
    
    def on_movement_start(self, callback):
        """
        Add a callback method that is executed when the sensor begins to detect movement.
        The callback method receives the Pin instance as unique input param.
        After an activation the driver waits for the reactivation_delay before to call
        the callback method again
        """
        self._callback_on = callback
        if callback is not None and self.is_active():
            self._monitor() # If the sensor is currently active the callback is called inmediatelly

    
    def on_movement_end(self, callback):
        """
        Add a callback method that is executed when the sensor stops to detect movementafter an activation.
        The callback method receives the Pin instance as unique input param.
        After an activation the driver waits for the reactivation_delay and if then 
        the sensor is not detecting movement then the callback method is called.
        If the sensor detect movement again, the counter is reinitiated.
        """
        self._callback_off = callback
    

