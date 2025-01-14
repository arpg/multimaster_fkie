# Software License Agreement (BSD License)
#
# Copyright (c) 2018, Fraunhofer FKIE/CMS, Alexander Tiderko
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Fraunhofer nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import division, absolute_import, print_function, unicode_literals

from concurrent import futures
import grpc
import rospy
import time

from fkie_multimaster_msgs.srv import LoadLaunch, LoadLaunchResponse
import fkie_multimaster_msgs.grpc.file_pb2_grpc as fgrpc
import fkie_multimaster_msgs.grpc.launch_pb2_grpc as lgrpc
import fkie_multimaster_msgs.grpc.monitor_pb2_grpc as mgrpc
import fkie_multimaster_msgs.grpc.screen_pb2_grpc as sgrpc
import fkie_multimaster_msgs.grpc.settings_pb2_grpc as stgrpc
import fkie_multimaster_msgs.grpc.version_pb2_grpc as vgrpc

from .common import interpret_path
from .file_servicer import FileServicer
from .launch_servicer import LaunchServicer
from .monitor_servicer import MonitorServicer
from .screen_servicer import ScreenServicer
from .settings_servicer import SettingsServicer
from .version_servicer import VersionServicer


class GrpcServer:

    def __init__(self):
        self.server = None
        self.settings_servicer = SettingsServicer()
        self.launch_servicer = LaunchServicer()
        self.monitor_servicer = MonitorServicer(self.settings_servicer.settings)
        rospy.Service('~start_launch', LoadLaunch, self._rosservice_start_launch)
        rospy.Service('~load_launch', LoadLaunch, self._rosservice_load_launch)

    def __del__(self):
        self.server.stop(3)
        self.launch_servicer = None
        self.monitor_servicer = None
        self.settings_servicer = None

    def start(self, url='[::]:12311'):
        rospy.loginfo("Start grpc server on %s" % url)
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        # create credentials
        # read in key and certificate
#         with open('/home/tiderko/grpc_cert/server.key', 'rb') as f:
#             private_key = f.read()
#         with open('/home/tiderko/grpc_cert/server.crt', 'rb') as f:
#             certificate_chain = f.read()
#         # create server credentials
#         server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain,),))
#         print("port: ", self.server.add_secure_port(url, server_credentials))
        insecure_port = self.server.add_insecure_port(url)
        while insecure_port == 0 and not rospy.is_shutdown():
            rospy.logwarn("can not add insecure channel to '%s', try again..." % url)
            time.sleep(2.)
            insecure_port = self.server.add_insecure_port(url)
        if insecure_port > 0:
            fgrpc.add_FileServiceServicer_to_server(FileServicer(), self.server)
            lgrpc.add_LaunchServiceServicer_to_server(self.launch_servicer, self.server)
            mgrpc.add_MonitorServiceServicer_to_server(self.monitor_servicer, self.server)
            sgrpc.add_ScreenServiceServicer_to_server(ScreenServicer(), self.server)
            stgrpc.add_SettingsServiceServicer_to_server(self.settings_servicer, self.server)
            vgrpc.add_VersionServiceServicer_to_server(VersionServicer(), self.server)
            self.server.start()
            rospy.loginfo("Server at '%s' started!" % url)

    def shutdown(self):
        self.launch_servicer.stop()
        self.monitor_servicer.stop()
        self.server.stop(3)

    def load_launch_file(self, path, autostart=False):
        self.launch_servicer.load_launch_file(interpret_path(path), autostart)

    def _rosservice_start_launch(self, request):
        rospy.loginfo("Service request to load and start %s" % request.path)
        self.launch_servicer.load_launch_file(interpret_path(request.path), True)
        return LoadLaunchResponse()

    def _rosservice_load_launch(self, request):
        rospy.loginfo("Service request to load %s" % request.path)
        self.launch_servicer.load_launch_file(interpret_path(request.path), False)
        return LoadLaunchResponse()
