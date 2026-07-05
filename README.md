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
