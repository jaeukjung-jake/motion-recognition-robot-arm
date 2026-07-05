# Motion Recognition 6-DOF Robot Arm

This project is a motion-recognition-based robotic arm control system developed as a team project in the Intelligent IoT Design course at Konkuk University.

The system recognizes human motion using OpenCV and MediaPipe, processes motion data through a server, and controls a 6-DOF robotic arm using Raspberry Pi-Arduino communication.

## Project Overview

The goal of this project was to connect human motion recognition with real robotic arm movement.

I was responsible for the robotic arm hardware and control system, including servo motor control, circuit configuration, Raspberry Pi-Arduino communication, and converting received coordinate data into robotic arm motion commands.

## System Architecture

```text
Human Motion
    ↓
OpenCV / MediaPipe
    ↓
Server
    ↓
Raspberry Pi
    ↓
Serial Communication
    ↓
Arduino
    ↓
Servo Motors
    ↓
6-DOF Robotic Arm Motion

## My Role

In this team project, I was responsible for the robotic arm hardware and control system.

My main responsibilities included:

- Building the 6-DOF robotic arm hardware
- Configuring the servo motor driving circuit
- Developing the Raspberry Pi code for server communication
- Implementing Raspberry Pi-Arduino serial communication
- Developing the Arduino code for servo motor control
- Receiving motion-recognition-based coordinate data from the server
- Converting received coordinate data into robotic arm motor angle commands
- Applying inverse kinematics and measured data-based correction to reduce coordinate conversion errors
- Improving motion stability by applying interpolation to prevent sudden angle changes
- Reducing shaking and discontinuous movement of the robotic arm

Through this role, I focused on connecting motion-recognition data with actual robotic arm movement.  
This project helped me understand how perception data, embedded communication, motor control, and hardware behavior must be integrated to build a stable robotic system.

---

motion-recognition-6dof-robot-arm/
│
├── README.md
│
├── raspberry_pi/
│   └── raspberry_pi_robot_arm_controller.py
│
└── arduino/
    └── robot_arm_servo_control.ino

raspberry_pi/raspberry_pi_robot_arm_controller.py

This Python script runs on the Raspberry Pi.

Main functions:

Communicates with the external server
Receives motion-recognition-based command data
Processes coordinate or angle command data
Sends control commands to the Arduino through serial communication
Acts as the bridge between the motion-recognition system and the robotic arm hardware
arduino/robot_arm_servo_control.ino

This Arduino sketch controls the servo motors of the robotic arm.

Main functions:

Receives serial commands from the Raspberry Pi
Parses servo angle data
Controls each servo motor of the 6-DOF robotic arm
Executes robotic arm movements based on received commands
Supports smoother robotic arm motion through controlled angle updates
