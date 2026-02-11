import json
import threading

from compas_rrc_driver.message import Message
from compas_rrc_driver.srv import RobotMessageCommand
from compas_rrc_driver.srv import RobotStringCommand


class RobotBaseServiceProvider(object):
    def __init__(self, node, streaming_interface, robot_state):
        self.node = node
        self.streaming_interface = streaming_interface
        self.robot_state = robot_state


class RobotMessageServiceProvider(RobotBaseServiceProvider):
    def __init__(self, node, service_name, streaming_interface, robot_state):
        super(RobotMessageServiceProvider, self).__init__(node, streaming_interface, robot_state)
        self.service = self.node.create_service(RobotMessageCommand, service_name, self.handle_service_call)

        self.node.get_logger().debug('Started message command service...')

    def handle_service_call(self, request, response):
        raise NotImplementedError()


class RobotStringServiceProvider(RobotBaseServiceProvider):
    def __init__(self, node, service_name, streaming_interface, robot_state):
        super(RobotStringServiceProvider, self).__init__(node, streaming_interface, robot_state)
        self.service = self.node.create_service(RobotStringCommand, service_name, self.handle_service_call)

        self.node.get_logger().debug('Started string command service...')

    def handle_service_call(self, request, response):
        # String command handler assumes the string is JSON encoded
        command = json.loads(request.command)

        wait_event = threading.Event()
        call_results = {}

        def robot_response_received(response_message):
            try:
                self.node.get_logger().debug('Received response message: key=%s' % response_message.key)
                call_results['response'] = json.dumps(response_message.to_data())
            except Exception as e:
                self.node.get_logger().error('Error while receiving response message: %s' % str(e))
                call_results['exception'] = str(e)
            finally:
                wait_event.set()

        # Command might be a single instruction or a list of them
        if 'instruction' in command:
            message = Message.from_data(command)
            self.robot_state.on(message.key, robot_response_received)
            self.streaming_interface.execute_instruction(message)

            response_data = ''

            if message.feedback_level > 0:
                wait_event.wait()

                if 'response' not in call_results:
                    raise Exception('Service response missing: result=%s' % str(call_results))

                response_data = call_results['response']

            response.response = response_data
            return response

        # Batched commands only return the last response
        elif 'instructions' in command:
            response_data = ''

            for single_command in command['instructions']:
                message = Message.from_data(single_command)
                self.streaming_interface.execute_instruction(message)

                if message.feedback_level > 0:
                    wait_event.wait()

                    if 'response' not in call_results:
                        raise Exception('Service response missing: result=%s' % str(call_results))

                    response_data = call_results['response']

            response.response = response_data
            return response

        else:
            raise ValueError('Unexpected command')
