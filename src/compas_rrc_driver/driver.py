#!/usr/bin/env python3
import logging
import select
import socket
import threading
import time
import timeit

import rclpy
from rclpy.executors import ExternalShutdownException

from compas_rrc_driver.event_emitter import EventEmitterMixin
from compas_rrc_driver.protocol import WireProtocol
from compas_rrc_driver.topics import RobotMessageTopicProvider
from compas_rrc_driver.srv import GetProtocolVersion

try:
    import queue
except ImportError:  # pragma: no cover
    import Queue as queue

CONNECTION_TIMEOUT = 5
QUEUE_TIMEOUT = 5
RECONNECT_DELAY = 1
SOCKET_SELECT_TIMEOUT = 1
QUEUE_MESSAGE_TOKEN = 0
QUEUE_TERMINATION_TOKEN = -1
QUEUE_RECONNECTION_TOKEN = -2
START_PROCESS_TIME = timeit.default_timer()
TIMING_START = dict()

LOGGER = logging.getLogger('compas_rrc_driver')


def _socket_debug_info(sock):
    if not sock:
        return 'socket=None'

    details = []

    try:
        details.append('fd={}'.format(sock.fileno()))
    except Exception:
        details.append('fd=?')

    try:
        details.append('local={}:{}'.format(*sock.getsockname()))
    except Exception:
        details.append('local=?')

    try:
        details.append('peer={}:{}'.format(*sock.getpeername()))
    except Exception:
        details.append('peer=?')

    return ', '.join(details)


def _set_socket_opts(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if hasattr(socket, 'TCP_KEEPIDLE'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
    if hasattr(socket, 'TCP_KEEPINTVL'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    if hasattr(socket, 'TCP_KEEPCNT'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)


def _close_socket(sock):
    if not sock:
        return

    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass

    try:
        sock.close()
    except Exception:
        pass


def _get_perf_counter():
    secs = timeit.default_timer() - START_PROCESS_TIME
    return int(secs * 1000)


class CurrentMessage(object):
    def __init__(self):
        self.clear()

    @property
    def state(self):
        if len(self.header) < WireProtocol.FIXED_HEADER_LEN:
            return 'recv_header'

        if len(self.header) == WireProtocol.FIXED_HEADER_LEN:
            if self.remaining_payload_bytes > 0:
                return 'recv_payload'
            elif self.remaining_payload_bytes == 0:
                return 'message_complete'
            else:
                raise Exception('Payload exceeds expected length. Header={}, Payload={}'.format(self.header, self.payload))
        else:
            raise Exception('Header exceeds expected length. Header={}, Payload={}'.format(self.header, self.payload))

    @property
    def protocol_version(self):
        return WireProtocol.get_protocol_version(self.header)

    @property
    def payload_length(self):
        message_length = WireProtocol.get_message_length(self.header)
        payload_length = message_length - WireProtocol.FIXED_HEADER_LEN
        return payload_length

    @property
    def remaining_payload_bytes(self):
        return self.payload_length - len(self.payload)

    @property
    def remaining_header_bytes(self):
        return WireProtocol.FIXED_HEADER_LEN - len(self.header)

    def append_header_chunk(self, chunk):
        if not chunk:
            raise socket.error('Socket broken, header chunk empty')

        self.header += chunk
        self.add_perf_marker('header_recv')

    def append_payload_chunk(self, chunk):
        self.payload += chunk
        self.add_perf_marker('payload_recv')

    def clear(self):
        self.header = b''
        self.payload = b''
        self.timing = list()

    def deserialize(self):
        return WireProtocol.deserialize(self.header, self.payload)

    def add_perf_marker(self, label):
        self.timing.append((label, _get_perf_counter()))


class RobotStateConnection(EventEmitterMixin):
    def __init__(self, node, host, port, on_fatal_error):
        super(RobotStateConnection, self).__init__()
        self.node = node
        self.on_fatal_error = on_fatal_error
        self.is_running = False
        self.host = host
        self.port = port
        self.socket = None
        self.thread = None

    def on_message(self, callback):
        self.on('message', callback)

    def on_socket_broken(self, callback):
        self.on('socket_broken', callback)

    def connect(self):
        self.is_running = True
        self.thread = threading.Thread(target=self.socket_worker, name='robot_state_socket', daemon=True)
        self.thread.start()

    def disconnect(self):
        self.is_running = False
        if self.thread:
            self.thread.join(CONNECTION_TIMEOUT)
        self._disconnect_socket()

    def _connect_socket(self):
        try:
            self.node.get_logger().info('Robot state: Connecting socket %s:%d' % (self.host, self.port))
            self.socket = socket.create_connection((self.host, self.port), CONNECTION_TIMEOUT)
            self.socket.settimeout(SOCKET_SELECT_TIMEOUT)
            _set_socket_opts(self.socket)
            self.node.get_logger().info('Robot state: Socket connected (%s)' % _socket_debug_info(self.socket))
        except Exception:
            self.node.get_logger().error('Cannot connect robot state: %s:%d' % (self.host, self.port))
            raise

    def _disconnect_socket(self):
        self.node.get_logger().info('Robot state: Disconnecting socket (%s)' % _socket_debug_info(self.socket))
        _close_socket(self.socket)
        self.socket = None

    def socket_worker(self):
        self.node.get_logger().info('Robot state: Worker started')
        current_message = CurrentMessage()
        version_already_checked = False

        while self.is_running:
            try:
                if not self.socket:
                    current_message.clear()
                    version_already_checked = False
                    self._connect_socket()

                current_message.add_perf_marker('select_before')
                readable, _writable, failed = select.select([self.socket], [], [self.socket], SOCKET_SELECT_TIMEOUT)
                current_message.add_perf_marker('select_after')

                if len(failed) > 0:
                    raise socket.error('No readable socket available')

                if len(readable) == 0:
                    self.node.get_logger().debug(
                        'Robot state: Select timeout while waiting for %s (header=%d, payload=%d, %s)'
                        % (current_message.state, len(current_message.header), len(current_message.payload), _socket_debug_info(self.socket))
                    )
                    raise socket.timeout('Socket selection timed out')

                if current_message.state == 'recv_header':
                    current_message.add_perf_marker('recv_before')
                    header_chunk = readable[0].recv(current_message.remaining_header_bytes)
                    self.node.get_logger().debug(
                        'Robot state: Received header chunk len=%d remaining_header=%d (%s)'
                        % (len(header_chunk), current_message.remaining_header_bytes, _socket_debug_info(self.socket))
                    )
                    current_message.append_header_chunk(header_chunk)

                if current_message.state == 'recv_payload':
                    if not version_already_checked:
                        server_protocol_version = current_message.protocol_version
                        if WireProtocol.VERSION != server_protocol_version:
                            raise Exception('Protocol version mismatch: Server={}, Client={}'.format(server_protocol_version, WireProtocol.VERSION))
                        version_already_checked = True

                    chunk = readable[0].recv(current_message.remaining_payload_bytes)
                    self.node.get_logger().debug(
                        'Robot state: Received payload chunk len=%d remaining_payload_before_append=%d (%s)'
                        % (len(chunk), current_message.remaining_payload_bytes, _socket_debug_info(self.socket))
                    )

                    if not chunk:
                        raise socket.error('Socket broken, payload chunk empty')

                    try:
                        current_message.append_payload_chunk(chunk)

                        if current_message.state == 'message_complete':
                            message = current_message.deserialize()
                            self.emit('message', message)
                            self.emit(WireProtocol.get_response_key(message), message)

                            if LOGGER.getEffectiveLevel() >= logging.DEBUG:
                                timing_sent_to_topic = _get_perf_counter()
                                ts = TIMING_START.get(message.feedback_id, timing_sent_to_topic)
                                LOGGER.debug(
                                    'F-ID={}, S-ID={}, {}, sent_to_topic={}, msg_len={}'.format(
                                        message.feedback_id,
                                        message.sequence_id,
                                        ', '.join(['{}={}'.format(k, v - ts) for k, v in current_message.timing]),
                                        timing_sent_to_topic - ts,
                                        len(current_message.header) + len(current_message.payload),
                                    )
                                )

                            current_message.clear()

                    except Exception as me:
                        self.node.get_logger().error('Exception while recv/deserialization of a message, skipping message. Exception=%s' % str(me))
                        current_message.clear()

            except socket.timeout:
                pass
            except socket.error as se:
                self.node.get_logger().error(
                    'Socket error on robot state interface: %s (%s)' % (str(se), _socket_debug_info(self.socket))
                )
                if self.is_running:
                    _close_socket(self.socket)
                    self.socket = None
                    current_message.clear()
                    version_already_checked = False
                    self.emit('socket_broken')
                    self.node.get_logger().warning('Robot state: Disconnection detected, waiting %d sec before reconnect...' % RECONNECT_DELAY)
                    time.sleep(RECONNECT_DELAY)
            except Exception as e:
                error_message = 'Exception on robot state interface: {}'.format(str(e))
                self.node.get_logger().error(error_message)
                self.on_fatal_error(error_message)
                break

        self.node.get_logger().info('Robot state: Worker stopped')


class StreamingInterfaceConnection(EventEmitterMixin):
    def __init__(self, node, host, port, on_fatal_error):
        super(StreamingInterfaceConnection, self).__init__()
        self.node = node
        self.on_fatal_error = on_fatal_error
        self.is_running = False
        self.host = host
        self.port = port
        self.queue = queue.Queue()
        self.thread = None
        self.socket = None

    def on_message_sent(self, callback):
        self.on('message_sent', callback)

    def on_socket_broken(self, callback):
        self.on('socket_broken', callback)

    def connect(self):
        self.is_running = True
        self.thread = threading.Thread(target=self.socket_worker, name='streaming_interface_socket', daemon=True)
        self.thread.start()

    def disconnect(self):
        if self.is_running:
            self.is_running = False

        if self.queue:
            self.queue.put((QUEUE_TERMINATION_TOKEN, None))

        if self.thread:
            self.thread.join(CONNECTION_TIMEOUT)

        self._disconnect_socket()

    def reconnect(self):
        if self.queue:
            self.queue.put((QUEUE_RECONNECTION_TOKEN, time.time()))

    def _connect_socket(self):
        try:
            self.node.get_logger().info('Streaming interface: Connecting socket %s:%d' % (self.host, self.port))
            self.socket = socket.create_connection((self.host, self.port), CONNECTION_TIMEOUT)
            self.socket.settimeout(CONNECTION_TIMEOUT)
            _set_socket_opts(self.socket)
            self.node.get_logger().info('Streaming interface: Socket connected (%s)' % _socket_debug_info(self.socket))
        except Exception:
            self.node.get_logger().error('Cannot connect streaming interface: %s:%d' % (self.host, self.port))
            raise

    def _disconnect_socket(self):
        self.node.get_logger().info('Streaming interface: Disconnecting socket (%s)' % _socket_debug_info(self.socket))
        _close_socket(self.socket)
        self.socket = None

    def execute_instruction(self, message):
        self.queue.put((QUEUE_MESSAGE_TOKEN, message))

    def socket_worker(self):
        self.node.get_logger().info('Streaming interface: Worker started')
        last_successful_connect = None

        while self.is_running:
            try:
                if not self.socket:
                    self._connect_socket()
                    last_successful_connect = time.time()

                token_type, message = self.queue.get(block=True, timeout=QUEUE_TIMEOUT)

                if token_type == QUEUE_MESSAGE_TOKEN:
                    if LOGGER.getEffectiveLevel() >= logging.DEBUG:
                        timing_incoming = _get_perf_counter()
                        TIMING_START[message.sequence_id] = timing_incoming

                    wire_message = WireProtocol.serialize(message)
                    _, writable, _ = select.select([], [self.socket], [], SOCKET_SELECT_TIMEOUT)

                    if len(writable) == 0:
                        raise socket.error('No writable socket available')

                    writable[0].sendall(wire_message)
                    self.node.get_logger().debug(
                        'Streaming interface: Sent full frame len=%d (%s)' % (len(wire_message), _socket_debug_info(self.socket))
                    )

                    if LOGGER.getEffectiveLevel() >= logging.DEBUG:
                        timing_sent = _get_perf_counter()
                        LOGGER.debug(
                            'S-ID={}, sent_to_robot={}, incoming={}, msg_len={}'.format(
                                message.sequence_id,
                                timing_sent - timing_incoming,
                                timing_incoming,
                                len(wire_message),
                            )
                        )
                    self.emit('message_sent', message, wire_message)
                elif token_type == QUEUE_TERMINATION_TOKEN:
                    self.node.get_logger().info('Signal to terminate, closing socket')
                    break
                elif token_type == QUEUE_RECONNECTION_TOKEN:
                    reconnection_timestamp = message
                    self.node.get_logger().info(
                        'Streaming interface: Reconnection token received ts=%s last_successful_connect=%s (%s)'
                        % (reconnection_timestamp, last_successful_connect, _socket_debug_info(self.socket))
                    )
                    if last_successful_connect is None or reconnection_timestamp >= last_successful_connect:
                        raise socket.error('Reconnection requested at {}'.format(message))
                    self.node.get_logger().info(
                        'Ignoring stale reconnection request issued at {} because last successful connection was at {}'.format(
                            reconnection_timestamp,
                            last_successful_connect,
                        )
                    )
                else:
                    raise Exception('Unknown token type')
            except queue.Empty:
                pass
            except socket.error as se:
                if self.is_running:
                    self.node.get_logger().error('Streaming interface: Socket error %s (%s)' % (str(se), _socket_debug_info(self.socket)))
                    _close_socket(self.socket)
                    self.socket = None
                    self.emit('socket_broken')
                    self.node.get_logger().warning('Streaming interface: Disconnection detected, waiting %d sec before reconnect...' % RECONNECT_DELAY)
                    time.sleep(RECONNECT_DELAY)
            except Exception as e:
                error_message = 'Exception on streaming interface worker: {}'.format(str(e))
                self.node.get_logger().error(error_message)
                self.on_fatal_error(error_message)
                break

        self.node.get_logger().info('Streaming interface: Worker stopped')


def main():
    debug = True
    robot_host_default = '127.0.0.1'

    LOGGER.setLevel(logging.DEBUG if debug else logging.INFO)

    rclpy.init()
    node = rclpy.create_node('compas_rrc_driver')

    node.declare_parameter('robot_ip_address', robot_host_default)
    node.declare_parameter('robot_streaming_port', 30101)
    node.declare_parameter('robot_state_port', 30201)
    node.declare_parameter('sequence_check_mode', 'none')

    robot_host = node.get_parameter('robot_ip_address').value
    robot_streaming_port = int(node.get_parameter('robot_streaming_port').value)
    robot_state_port = int(node.get_parameter('robot_state_port').value)
    sequence_check_mode = node.get_parameter('sequence_check_mode').value

    node.declare_parameter('protocol_version', WireProtocol.VERSION)

    def handle_protocol_version(_request, response):
        response.version = int(WireProtocol.VERSION)
        return response

    node.create_service(GetProtocolVersion, 'get_protocol_version', handle_protocol_version)

    shutdown_reason = {'error': None}

    def on_fatal_error(error_message):
        shutdown_reason['error'] = error_message

    streaming_interface = None
    robot_state = None
    topic_provider = None

    try:
        node.get_logger().info(
            'Connecting robot %s (ports %d & %d, sequence check mode=%s)'
            % (robot_host, robot_streaming_port, robot_state_port, sequence_check_mode)
        )
        streaming_interface = StreamingInterfaceConnection(node, robot_host, robot_streaming_port, on_fatal_error)
        streaming_interface.connect()

        robot_state = RobotStateConnection(node, robot_host, robot_state_port, on_fatal_error)
        robot_state.connect()

        robot_state.on_socket_broken(streaming_interface.reconnect)

        def message_received_log(message):
            node.get_logger().debug('Received: "%s", content: %s' % (message.feedback, str(message).replace('\n', '; ')))
            node.get_logger().info(
                'Received message: feedback=%s, sequence_id=%d, feedback_id=%d'
                % (message.feedback, message.sequence_id, message.feedback_id)
            )

        def message_sent_log(message, wire_message):
            node.get_logger().debug('Sent: "%s", content: %s' % (message.instruction, str(message).replace('\n', '; ')))
            node.get_logger().info(
                'Sent message with length=%d, instruction=%s, sequence id=%d'
                % (len(wire_message), message.instruction, message.sequence_id)
            )

        streaming_interface.on_message_sent(message_sent_log)
        if debug:
            robot_state.on_message(message_received_log)

        options = dict(sequence_check_mode=sequence_check_mode)
        topic_provider = RobotMessageTopicProvider(node, 'robot_command', 'robot_response', streaming_interface, robot_state, options=options)

        while rclpy.ok() and shutdown_reason['error'] is None:
            rclpy.spin_once(node, timeout_sec=0.1)

        if shutdown_reason['error']:
            node.get_logger().error('Shutting down due to fatal worker error: %s' % shutdown_reason['error'])

    except ExternalShutdownException:
        pass
    finally:
        if topic_provider:
            node.get_logger().info('Disconnecting topic provider...')
            topic_provider.disconnect()

        if streaming_interface:
            node.get_logger().info('Disconnecting streaming interface...')
            streaming_interface.disconnect()

        if robot_state:
            node.get_logger().info('Disconnecting robot state...')
            robot_state.disconnect()

        node.get_logger().info('Terminated')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
