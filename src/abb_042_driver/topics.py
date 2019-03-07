import rospy
from abb_042_driver import msg
from abb_042_driver.message import Message


class AbbMessageTopicProvider(object):
    def __init__(self, topic_name, streaming_interface):
        super(AbbMessageTopicProvider, self).__init__()

        self.streaming_interface = streaming_interface
        self.topic = rospy.Subscriber(topic_name, msg.AbbMessage, self.callback)

        rospy.logdebug('Subscribed to message topic %s...', topic_name)

    def callback(self, ros_message):
        message = Message.from_ros_message(ros_message)
        self.streaming_interface.execute_instruction(message)
