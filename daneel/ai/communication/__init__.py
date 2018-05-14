import threading
import serial
import time
from collections import deque
from communication.message_definition import *

SERIAL_BAUDRATE = 115200
SERIAL_PATH = "/dev/ttyAMA0"
SERIAL_SEND_TIMEOUT = 500  # ms


class Communication:
    def __init__(self, serial_path=SERIAL_PATH, baudrate=SERIAL_BAUDRATE):
        """
        ctor of the communication class
        :param serial_path: The path of the serial file
        :type serial_path: str
        :param baudrate: The baudrate of UART (must the same as the one on the other board)
        :type baudrate: int
        """
        self._serial_port = serial.Serial(serial_path, baudrate)
        self._current_msg_id = 0  # type: int
        self._mailbox = deque()
        self.mock_communication = False  # Set to True if Serial is not plugged to the Teensy
        self._callbacks = {msg_type: [] for msg_type in eTypeUp}
        self._serial_lock = threading.Lock()
        self.reset_soft_teensy()
        self.eTypeUp = eTypeUp  # For exposure purposes

    def register_callback(self, message_type, callback):
        if message_type not in self._callbacks:
            return
        self._callbacks[message_type].append(callback)

    def send_speed_command(self, vx, vy, vtheta, max_retries=1000):
        msg = sMessageDown()
        msg.type = eTypeDown.SPEED_COMMAND
        msg.data = sSpeedCommand()
        msg.data.vx = vx
        msg.data.vy = vy
        msg.data.vtheta = vtheta
        return self.send_message(msg, max_retries)

    def send_hmi_command(self, red_led_cmd, green_led_cmd, blue_led_cmd, max_retries=1000):
        """
        /!\ Blocking command (try to send the message until it has been received)
        Send an HMI (LED) command to the teensy.
        :param red_led_cmd: Red value (0 - 255, then casted to 3 bits)
        :type red_led_cmd: int
        :param green_led_cmd: Green value (0 - 255, then casted to 3 bits)
        :type green_led_cmd: int
        :param blue_led_cmd: Blue value (0 - 255, then casted to 2 bits)
        :type blue_led_cmd: int
        :return: 0 if message has been sent, -1 if max retries has been reached
        :rtype:
        """
        msg = sMessageDown()
        msg.type = eTypeDown.HMI_COMMAND
        msg.data = sHMICommand()
        msg.data.hmi_command = (red_led_cmd & 0b11100000) | (green_led_cmd >> 3 & 0b00011100) | (blue_led_cmd >> 6
                                                                                                 & 0b00000011)
        return self.send_message(msg, max_retries)

    def send_actuator_command(self, actuator_id, actuator_value, max_retries=1000):
        msg = sMessageDown()
        msg.type = eTypeDown.ACTUATOR_COMMAND
        msg.data = sActuatorCommand()
        msg.data.actuator_id = actuator_id
        msg.data.actuator_command = actuator_value
        return self.send_message(msg, max_retries)

    def send_sensor_command(self, sensor_id, command_state, max_retries=1000):
        msg = sMessageDown()
        msg.type = eTypeDown.SENSOR_COMMAND
        msg.data = sSensorCommand()
        msg.data.sensor_id = sensor_id
        msg.data.sensor_state = command_state
        return self.send_message(msg, max_retries)

    def reset_soft_teensy(self, max_retries=1000):
        if self.mock_communication:
            print("[Communication] Warning : Teensy communication mocked !")
            return 0
        msg = sMessageDown()
        msg.type = eTypeDown.RESET
        for i in range(100):
             self._serial_port.read_all()
             time.sleep(0.01)
        ret = self.send_message(msg, max_retries)
        if ret == 0:
            self._current_msg_id = 0
            self._mailbox = deque()
        return ret

    def send_theta_repositionning(self, theta, max_retries=1000):
        msg = sMessageDown()
        msg.type = eTypeDown.THETA_REPOSITIONING
        msg.data = sThetaRepositioning()
        msg.data.theta_repositioning = theta
        return self.send_message(msg, max_retries)

    def send_message(self, msg, max_retries=1000):
        """
        Send message via Serial (defined during the instantiation of the class)
        :param msg: the message to send
        :type msg: sMessageDown
        :param max_retries: the maximum number of resend (on timeout = SERIAL_SEND_TIMEOUT or on NON_ACK) before failing
        :type max_retries: int
        :return: 0 if the message is sent, -1 if max_retries has been reached
        :rtype: int
        """
        if self.mock_communication:
            max_retries = 0

        self._serial_lock.acquire()
        msg.down_id = self._current_msg_id
        self._current_msg_id = (self._current_msg_id + 1) % 256
        serialized = msg.serialize().tobytes()
        for i in range(max_retries):
            # print(serialized)
            self._serial_port.write(serialized)
            time_sent = int(round(time.time() * 1000))
            while self._serial_port.in_waiting < UP_MESSAGE_SIZE:
                if int(round(time.time() * 1000)) - time_sent > SERIAL_SEND_TIMEOUT:
                    break  # waiting for ack
            if self._serial_port.in_waiting >= UP_MESSAGE_SIZE:
                packed = self._serial_port.read(UP_MESSAGE_SIZE)
                up_msg = sMessageUp()
                try:
                    up_msg.deserialize(packed)
                except DeserializationException as e:
                    print("[Comm] Message synchronisation lost : Trying to re synchronise")
                    while not self._serial_port.in_waiting:
                        time.sleep(0.1)
                    self._serial_port.read(1)  # Read one byte and retry. Until synchro is ok.
                    continue

                self._handle_acknowledgement(up_msg)
                if up_msg.type == eTypeUp.ACK_DOWN:
                    self._serial_lock.release()
                    return 0  # success
                else:
                    self._mailbox.append(up_msg)  # if it is not an ACK or a NONACK, store it to deliver later
        self._serial_lock.release()
        return -1  # failure

    def _send_acknowledgment(self, id_to_acknowledge):
        ack = sMessageDown()
        ack.down_id = self._current_msg_id
        self._current_msg_id = (self._current_msg_id + 1) % 256
        ack.type = eTypeDown.ACK_UP
        ack.data = sAckUp()
        ack.data.ack_up_id = id_to_acknowledge
        serialized = ack.serialize().tobytes()
        self._serial_port.write(serialized)

    def _send_odometry_report_acknowledgment(self, msg_id, odom_id):
        ack = sMessageDown()
        ack.down_id = self._current_msg_id
        self._current_msg_id = (self._current_msg_id + 1) % 256
        ack.type = eTypeDown.ACK_ODOM_REPORT
        ack.data = sAckOdomReport()
        ack.data.ack_up_id = msg_id
        ack.data.ack_odom_report_id = odom_id
        serialized = ack.serialize().tobytes()
        self._serial_port.write(serialized)

    def _handle_acknowledgement(self, msg):
        if msg.type == eTypeUp.ACK_DOWN:
            return
        elif msg.type == eTypeUp.ODOM_REPORT:
            self._send_odometry_report_acknowledgment(msg.up_id, msg.data.new_report_id)
        else:
            self._send_acknowledgment(msg.up_id)

    def check_message(self, max_read=1):
        """
        Check if there is any incoming message on the Serial (defined during the instantiation of the class)
        and returns the oldest message.
        :return: The oldest message non read
        :rtype: sMessageUp
        """
        if self.mock_communication:
            return

        self._serial_lock.acquire()
        for i in range(max_read):
            if self._serial_port.in_waiting >= UP_MESSAGE_SIZE:
                try:
                    packed = self._serial_port.read(UP_MESSAGE_SIZE)
                    up_msg = sMessageUp()
                    up_msg.deserialize(packed)
                except DeserializationException as e:
                    print("[Comm] Message synchronisation lost : Trying to re synchronise")
                    while not self._serial_port.in_waiting:
                        time.sleep(0.1)
                    self._serial_port.read(1)  # Read one byte and retry. Until synchro is ok.
                    continue
                self._handle_acknowledgement(up_msg)
                self._mailbox.append(up_msg)
        self._serial_lock.release()

        for i in range(max_read):
            if len(self._mailbox) > 0:
                msg = self._mailbox.popleft()
                self.handle_message(msg)

    def handle_message(self, message):
        """

        :param message:
        :type message: sMessageUp
        :return:
        :rtype:
        """
        if message.type == eTypeUp.SENSOR_VALUE:
            for cb in self._callbacks[eTypeUp.SENSOR_VALUE]:
                cb(message.data.sensor_id, message.data.sensor_value)
        elif message.type == eTypeUp.HMI_STATE:
            cord_state = bool(message.data.hmi_state & (1 << 7))
            button1_state = bool(message.data.hmi_state & (1 << 6))
            button2_state = bool(message.data.hmi_state & (1 << 5))
            red_led_state = bool(message.data.hmi_state & (1 << 4))
            green_led_state = bool(message.data.hmi_state & (1 << 3))
            blue_led_state = bool(message.data.hmi_state & (1 << 2))
            for cb in self._callbacks[eTypeUp.HMI_STATE]:
                cb(cord_state, button1_state, button2_state, red_led_state, green_led_state, blue_led_state)
        elif message.type == eTypeUp.ODOM_REPORT:

            for cb in self._callbacks[eTypeUp.ODOM_REPORT]:
                cb(message.data.previous_report_id, message.data.new_report_id, message.data.dx, message.data.dy,
                   message.data.dtheta)
        elif message.type == eTypeUp.ACK_DOWN:
            pass

