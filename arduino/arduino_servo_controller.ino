/*
Motion Recognition 6-DOF Robot Arm Project

This Arduino sketch controls the servo motors of a 6-DOF robotic arm.
It receives angle commands from Raspberry Pi through serial communication
and converts them into servo motor movements.

Main roles:
- Receives serial commands from Raspberry Pi
- Parses servo angle data
- Controls each servo motor of the robotic arm
- Executes motion commands smoothly

Author: Jaeuk Jung
Project: Motion Recognition 6-DOF Robot Arm
*/

#include <Servo.h>
#include <math.h> // 가감속 계산(cos)을 위해 필요

// ===== 서보 핀 설정 =====
const int SERVO_PINS[7] = {3, 5, 6, 7, 9, 10, 11};

// ===== 서보 객체 =====
Servo servos[7];

// 정밀한 위치 계산을 위해 float형 사용 (초기값 0.0)
float currentAngles[7] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

// ===== 서보 초기화 =====
void setup() {
  Serial.begin(115200);
  Serial.println("7 Servo Smooth Control Ready");

  for (int i = 0; i < 7; i++) {
    // 1. attach 전에 0도로 설정하여 튀는 현상 방지
    servos[i].write(0);
    
    // 2. 핀 연결
    servos[i].attach(SERVO_PINS[i], 500, 2400);
    
    // 3. 변수 초기화
    currentAngles[i] = 0.0;
    
    // 초기화 안정화 대기
    delay(200);
    
    Serial.print("Servo ");
    Serial.print(i + 1);
    Serial.println(" attached at 0 deg (Fixed)");
  }

  Serial.println("All servos ready at 0!");
  delay(500);
}

// ===== 부드러운 이동 함수 (Ease-In/Ease-Out) =====
// targetAngles: 목표 각도 배열
// durationMs: 이동하는 데 걸리는 전체 시간 (ms)
void moveToSmooth(int targetAngles[7], int durationMs) {
  
  // 1. 이동 시작 전 상태 저장
  float startAngles[7];
  float changeAngles[7];
  
  for (int i = 0; i < 7; i++) {
    startAngles[i] = currentAngles[i];
    changeAngles[i] = targetAngles[i] - startAngles[i];
  }

  // 2. 시간 흐름에 따른 위치 계산 루프
  unsigned long startTime = millis();
  int timeStep = 15; // 루프 주기 (작을수록 부드럽지만 연산량 증가)

  while (true) {
    unsigned long currentTime = millis();
    unsigned long elapsedTime = currentTime - startTime;

    // 시간이 다 되면 루프 탈출
    if (elapsedTime >= durationMs) break;

    // 진행률 (0.0 ~ 1.0)
    float progress = (float)elapsedTime / durationMs;

    // [핵심] Ease-In-Out 공식 (코사인 보간)
    // -0.5 * (cos(PI * progress) - 1) -> S자 곡선을 만듦
    float easeFactor = -0.5 * (cos(PI * progress) - 1.0);

    // 각 서보 위치 업데이트
    for (int i = 0; i < 7; i++) {
      float newAngle = startAngles[i] + (changeAngles[i] * easeFactor);
      
      // 서보에는 int형으로 변환하여 전달
      servos[i].write((int)newAngle);
      
      // 현재 위치 기억 (다음 계산을 위해 float 유지)
      currentAngles[i] = newAngle;
    }
    
    delay(timeStep);
  }

  // 3. 최종 목표값으로 정확하게 보정 (오차 제거)
  for (int i = 0; i < 7; i++) {
    servos[i].write(targetAngles[i]);
    currentAngles[i] = (float)targetAngles[i];
  }
}

// ===== 명령 수신 및 실행 =====
void loop() {
  static String input = "";

  if (Serial.available() > 0) {
    input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("MOVE")) {
      int targetAngles[7] = {0};
      
      // 기존 핀 매핑 유지 ([5], [4], [3] 순서 주의)
      int parsed = sscanf(input.c_str(), "MOVE %d %d %d %d %d %d %d",
                          &targetAngles[0], &targetAngles[1], &targetAngles[2],
                          &targetAngles[5], &targetAngles[4], &targetAngles[3],
                          &targetAngles[6]);

      if (parsed == 7) {
        Serial.print("Received MOVE: ");
        for (int i = 0; i < 7; i++) {
          Serial.print(targetAngles[i]);
          if (i < 6) Serial.print(", ");
        }
        Serial.println();
        
        // ===== [설정] 이동 시간 조절 =====
        // 1000 = 1초, 2000 = 2초
        // 이 값을 조절하여 전체 동작의 속도를 결정합니다.
        int moveDuration = 2000; 
        
        moveToSmooth(targetAngles, moveDuration); 
        
        Serial.println("Smooth move complete.");
      } else {
        Serial.println("Invalid MOVE command format.");
      }
    }
  }
}
