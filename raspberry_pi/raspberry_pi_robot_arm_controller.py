"""
Motion Recognition 6-DOF Robot Arm Project

This Raspberry Pi script receives motion-recognition-based command data
from the server and sends converted control commands to the Arduino board.

Main roles:
- Communicates with the external server
- Receives motion or coordinate command data
- Converts command data into robot arm control signals
- Sends servo angle commands to Arduino through serial communication

Author: Jaeuk Jung
Project: Motion Recognition 6-DOF Robot Arm
"""

import serial
import time
import websocket
import json
import threading
import ssl
import RPi.GPIO as GPIO
import socket
import cv2        # [추가] OpenCV
import base64     # [추가] 이미지 인코딩용

# ==========================================
# ★ [핵심 1] IPv6 강제 차단 (DNS 납치 코드)
# ==========================================
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

# ==========================================
# 1. 설정 및 전역 변수
# ==========================================
ARDUINO_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200
SERVER_URL = "wss://gapingly-hemeralopic-hayley.ngrok-free.dev/ws/motion"
VIDEO_SERVER_URL = "wss://gapingly-hemeralopic-hayley.ngrok-free.dev/ws/video"
BUTTON_PIN = 17

HEARTBEAT_ACTIVE = False
arduino = None
threads_started = False
ws_holder = [None] # motion (제어) 용
video_ws_holder = [None] # ★ [추가] video (영상) 용
latest_angles = None
data_lock = threading.Lock()

# [영상 설정]
CAMERA_WIDTH = 160   # 해상도를 낮춰야 전송 속도가 빠름 (640은 느릴 수 있음)
CAMERA_HEIGHT = 120
JPEG_QUALITY = 30    # 이미지 품질 (0~100), 낮을수록 빠름

# ==========================================
# 2. GPIO 설정
# ==========================================
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ==========================================
# 3. 아두이노 연결
# ==========================================
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print(f"✅ 아두이노 연결 성공")
except Exception as e:
    print(f"❌ 아두이노 연결 실패 (테스트 모드): {e}")

# ==========================================
# 4. 스레드 로직
# ==========================================
def arduino_worker_thread():
    """ 아두이노 제어 스레드 """
    global latest_angles
    print("🚜 [Thread] 아두이노 제어 시작")
    last_sent_angles = None

    while True:
        if not HEARTBEAT_ACTIVE:
            time.sleep(1)
            continue

        current_target = None
        with data_lock:
            if latest_angles is not None:
                current_target = latest_angles[:]
        
        if current_target and current_target != last_sent_angles:
            if arduino and arduino.is_open:
                try:
                    angles_str = ' '.join(map(str, current_target))
                    cmd = f"MOVE {angles_str}\r\n"
                    arduino.write(cmd.encode())
                    arduino.reset_input_buffer()
                    last_sent_angles = current_target
                    # print(f"📤 [Arduino] {cmd.strip()}") # 로그 너무 많으면 주석 처리
                except Exception as e:
                    print(f"⚠️ Serial Error: {e}")
        time.sleep(0.2)

def send_heartbeat_thread(ws_list):
    """ 서버 연결 유지용 하트비트 """
    print("💓 [Thread] 하트비트 시작")
    while True:
        if HEARTBEAT_ACTIVE and ws_list[0]:
            try:
                ws_list[0].send(json.dumps({"type": "PING"}))
                time.sleep(5)
            except:
                pass
        else:
            time.sleep(1)

def button_check_thread(ws_list):
    """ 버튼 감지 스레드 """
    print("🔘 [Thread] 버튼 감지 시작")
    while True:
        if HEARTBEAT_ACTIVE and ws_list[0] and GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            try:
                print("🔘 버튼 눌림! 서버로 전송...")
                ws_list[0].send(json.dumps({"type": "button pressed"}))
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ 버튼 에러: {e}")
        time.sleep(0.05)

# ★★★ [신규 추가] 영상 전송 스레드 ★★★
def camera_stream_thread(ws_list):
    """ 별도의 WebSocket을 통해 카메라 영상을 서버로 스트리밍 """
    print("📷 [Thread] 카메라 스트리밍 시작")
    cap = cv2.VideoCapture(0)
    
    # 카메라 해상도 설정 (데이터량 줄이기 위함)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    
    while True:
        # 서버 연결이 끊겨 있으면 카메라 읽기도 잠시 쉼
        # video_ws_list[0]이 연결되어 있는지 확인
        if not HEARTBEAT_ACTIVE or not ws_list[0]: 
            time.sleep(1)
            continue
            
        ret, frame = cap.read()
        if ret:
            try:
                # 1. 이미지 압축 (JPEG)
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                
                # 2. Base64로 인코딩 (바이트 -> 문자열)
                img_str = base64.b64encode(buffer).decode('utf-8')
                
                # 3. 웹소켓 전송 (ws_list[0]은 video_ws_holder의 연결 객체)
                payload = {
                    "type": "VIDEO",
                    "image": img_str
                }
                ws_list[0].send(json.dumps(payload))
                
                # 4. 전송 속도 조절
                time.sleep(0.06) 
                
            except Exception as e:
                # print(f"📷 카메라 에러: {e}") # 연결 끊김 시 에러가 많이 발생할 수 있습니다
                time.sleep(1)
        else:
            # print("📷 프레임 읽기 실패")
            time.sleep(1)

    cap.release()

# ==========================================
# 5. WebSocket 이벤트
# ==========================================
def video_connect_thread():
    """ 영상 전송용 WebSocket을 연결하고 유지하는 스레드 """
    global video_ws_holder
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    print(f"🚀 [Video] 접속 시도: {VIDEO_SERVER_URL}")

    while True:
        try:
            video_ws = websocket.WebSocketApp(
                VIDEO_SERVER_URL,
                on_open=on_video_open,
                on_close=on_video_close,
                on_error=on_video_error,
                header={
                    "ngrok-skip-browser-warning": "true",
                    "User-Agent": "RaspberryPi_Robot_Video"
                }
            )
            # run_forever가 블로킹하므로, 연결이 끊길 때까지 재시도하지 않습니다.
            video_ws.run_forever(sslopt={"context": ssl_context}, ping_interval=10, ping_timeout=5)
            
        except Exception as e:
            print(f"⚠️ [Video] 실행 중 에러: {e}")
        
        # 연결이 끊어지면 (on_video_close 또는 에러 발생)
        video_ws_holder[0] = None # 연결 끊김 표시
        print("🔄 [Video] 3초 후 재접속 시도...")
        time.sleep(3)


def on_video_open(ws):
    global video_ws_holder
    print("✅ [Video 연결 성공] 영상 통신 시작!")
    video_ws_holder[0] = ws
    ws.send(json.dumps({"type": "VIDEO_INIT"}))

def on_video_close(ws, status, msg):
    global video_ws_holder
    video_ws_holder[0] = None
    print("🔌 [Video] 연결 끊김.")

def on_video_error(ws, error):
    print(f"🚫 [Video 통신 에러]: {error}")


# ★★★ [수정] 로봇 제어용 on_open 함수 ★★★
def on_open(ws):
    global HEARTBEAT_ACTIVE, threads_started, ws_holder
    print("\n✅ [Motion 연결 성공] 서버와 통신 시작!")
    
    HEARTBEAT_ACTIVE = True
    ws_holder[0] = ws
    
    ws.send(json.dumps({"type": "ROBOT_INIT"}))
    
    if not threads_started:
        # 1. 기존 스레드들 (motion 관련)
        threading.Thread(target=arduino_worker_thread, daemon=True).start()
        threading.Thread(target=send_heartbeat_thread, args=(ws_holder,), daemon=True).start()
        threading.Thread(target=button_check_thread, args=(ws_holder,), daemon=True).start()
        
        # 2. ★ [추가] 영상 전송 전용 연결 스레드 시작
        threading.Thread(target=video_connect_thread, daemon=True).start()
        
        # 3. ★ [수정] 카메라 스트림 스레드 시작 (video_ws_holder 사용)
        threading.Thread(target=camera_stream_thread, args=(video_ws_holder,), daemon=True).start()
        
        threads_started = True

def on_message(ws, message):
    global latest_angles
    try:
        if not message: return
        data = json.loads(message)
        if data.get("type") == "CONTROL":
            angles = data.get("angles")
            if angles:
                with data_lock:
                    latest_angles = angles
    except:
        pass

def on_close(ws, status, msg):
    global HEARTBEAT_ACTIVE
    HEARTBEAT_ACTIVE = False
    print("🔌 연결 끊김. 재접속 대기...")

def on_error(ws, error):
    print(f"🚫 [통신 에러]: {error}")

# ==========================================
# 6. 메인 실행
# ==========================================
if __name__ == "__main__":
    websocket.enableTrace(False)
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    print(f"🚀 [Motion] 접속 시도: {SERVER_URL}")

    try:
        while True:
            try:
                # 메인 루프는 'ws/motion' 연결만 담당
                ws = websocket.WebSocketApp(
                    SERVER_URL,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    header={
                        "ngrok-skip-browser-warning": "true",
                        "User-Agent": "RaspberryPi_Robot"
                    }
                )
                ws.run_forever(sslopt={"context": ssl_context}, ping_interval=10, ping_timeout=5)
                
            except Exception as e:
                print(f"⚠️ [Motion] 실행 중 에러: {e}")
            
            print("🔄 [Motion] 3초 후 재접속 시도...")
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n👋 프로그램 종료")
    finally:
        GPIO.cleanup()
        if arduino and arduino.is_open:
            arduino.close()
