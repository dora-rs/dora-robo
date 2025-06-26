import socketio
import time
import threading
import requests
import json
import cv2

def cameras_to_stream_json(cameras: dict[str, int]):
    """
    将摄像头字典转换为包含流信息的 JSON 字符串。
    
    参数:
        cameras (dict[str, int]): 摄像头名称到 ID 的映射
    
    返回:
        str: 格式化的 JSON 字符串
    """
    stream_list = [{"id": cam_id, "name": name} for name, cam_id in cameras.items()]
    result = {
        "total": len(stream_list),
        "streams": stream_list
    }
    return json.dumps(result)

class RobotClient:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.session = requests.Session()

        self.running = False
        self.last_heartbeat_time = 0
        self.heartbeat_interval = 2  # 心跳间隔(秒)

        self.cameras: dict[str, int] = {
            "image_top": 1,
            "image_depth_top": 2,
        } # Default Config
        
        # 注册事件处理
        self.sio.on('HEARTBEAT_RESPONSE', self.__on_heartbeat_response_handle)
        self.sio.on('connect', self.__on_connect_handle)
        self.sio.on('disconnect', self.__on_disconnect_handle)
        self.sio.on('robot_command', self.__on_robot_command_handle)
    
####################### Client Start/Stop ############################
    def start(self):
        """启动客户端"""
        self.running = True
        self.sio.connect(self.server_url)
        
        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        
        # print("客户端已启动，等待连接...")
    
    def stop(self):
        """停止客户端"""
        self.running = False
        self.sio.disconnect()
        print("客户端已停止")
    
####################### Client Handle ############################
    def __on_heartbeat_response_handle(self, data):
        """心跳响应回调"""
        print("收到心跳响应:", data)
    
    def __on_connect_handle(self):
        """连接成功回调"""
        print("成功连接到服务器")
        
        # # 初始化视频流列表
        # try:
        #     response = self.session.post(
        #         f"{self.server_url}/robot/stream_info",
        #         json = cameras_to_stream_json(self.cameras),
        #     )
        #     print("初始化视频流列表:", response.json())
        # except Exception as e:
        #     print(f"初始化视频流列表失败: {e}")
    
    def __on_disconnect_handle(self):
        """断开连接回调"""
        print("与服务器断开连接")
    
    def __on_robot_command_handle(self, data):
        """收到机器人命令回调"""
        print("收到服务器命令:", data)
        
        # 根据命令类型进行响应
        if data.get('cmd') == 'video_list':
            print("处理更新视频流命令...")
            response_data = cameras_to_stream_json(self.cameras)
            # 发送响应
            try:
                response = self.session.post(
                    f"{self.server_url}/robot/stream_info",
                    json = response_data,
                )
                print(f"已发送响应 [{data.get('cmd')}]: {response_data}")
            except Exception as e:
                print(f"发送响应失败 [{data.get('cmd')}]: {e}")
            
        elif data.get('cmd') == 'start_collection':
            print("处理开始采集命令...")
            
            # 发送响应
            self.send_response('start_collection', "success")
        
        elif data.get('cmd') == 'finish_collection':
            # 模拟处理完成采集
            print("处理完成采集命令...")
            time.sleep(0.01)  # 模拟处理时间
            
            # 准备响应数据
            response_data = {
                "msg": "success",
                "data": {
                    "file_message": {
                        "file_name": "叠衣服001001",
                        "file_local_path": "/home/agilex/data/叠衣服001001",
                        "file_size": "3.2",
                        "file_duration": "30"
                    },
                    "verification": {
                        "file_integrity": "pass",
                        "camera_frame_rate": "pass"
                    }
                }
            }           
            # 发送响应
            self.send_response('finish_collection', response_data['msg'], response_data)
        
        elif data.get('cmd') == 'discard_collection':
            # 模拟处理丢弃采集
            print("处理丢弃采集命令...")
            time.sleep(0.01)  # 模拟处理时间
            
            # 发送响应
            self.send_response('discard_collection', "success")
        
        elif data.get('cmd') == 'submit_collection':
            # 模拟处理提交采集
            print("处理提交采集命令...")
            time.sleep(0.01)  # 模拟处理时间
            
            # 发送响应
            self.send_response('submit_collection', "success")
    
####################### Client Send to Server ############################
    def send_heartbeat(self):
        """定期发送心跳"""
        while self.running:
            current_time = time.time()
            if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                try:
                    self.sio.emit('HEARTBEAT')
                    self.last_heartbeat_time = current_time
                except Exception as e:
                    print(f"发送心跳失败: {e}")
            time.sleep(1)
            self.sio.wait()
         

    # 心跳包二次回复请求
    def send_response(self, cmd, msg, data=None):
        """发送心跳包二次回复请求到服务器"""
        try:
            payload = {"cmd": cmd, "msg": msg}
            if data:
                payload.update(data)
            
            response = self.session.post(
                f"{self.server_url}/robot/response",
                json=payload
            )
            print(f"已发送响应 [{cmd}]: {payload}")
        except Exception as e:
            print(f"发送响应失败 [{cmd}]: {e}")

####################### Robot API ############################
    def stream_info(self, info: dict[str, int]):
        self.cameras = info.copy()
        print(f"更新摄像头信息: {self.cameras}")

    def update_stream_info_to_server(self):
        stream_info_data = cameras_to_stream_json(self.cameras)
        print(f"stream_info_data: {stream_info_data}")

        response = self.session.post(
            f"{self.server_url}/robot/stream_info",
            json = stream_info_data,
        )

    def update_stream(self, name, frame):

        _, jpeg_frame = cv2.imencode('.jpg', frame, 
                            [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        frame_data = jpeg_frame.tobytes()

        stream_id = self.cameras[name]
        # Build URL
        url = f"{self.server_url}/robot/update_stream/{stream_id}"

        # Send POST request
        try:
            response = self.session.post(url, data=frame_data)
            if response.status_code != 200:
                print(f"Server returned error: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")


# if __name__ == '__main__':
#     client = RobotClient()
    
#     try:
#         client.start()
#     except KeyboardInterrupt:
#         client.stop()