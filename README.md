# YOLOv8Lume: Smart Home Lighting Control with Human Detection

YOLOv8Lume is an intelligent lighting control system that uses deep learning (YOLOv8) and IoT (ESP32) to optimize energy usage through real-time human detection. The system provides a user-friendly mobile app interface for real-time control and monitoring, making smart homes more energy-efficient and convenient.

## Table of Contents
- [Introduction](#introduction)
- [Implementation](#implementation)
- [Analysis](#analysis)
- [Software Details](#software-details)
- [Hardware Details](#hardware-details)
- [Design Details](#design-details)
- [Troubleshooting](#troubleshooting)

---

## Introduction
The YOLOv8Lume project addresses energy efficiency in smart homes by using deep learning and IoT. By detecting human presence, the system controls lighting in real-time, reducing unnecessary energy usage and providing a better user experience.

## Implementation
This project involves integrating hardware and software components. The system consists of:
- **Backend**: Python and Flask-based web server.
- **Mobile Application**: Developed with Flutter/Dart for real-time occupancy updates.
- **Deep Learning Model**: YOLOv8 for human detection.
- **Hardware**: ESP32, relay modules, HD camera, LED bulbs.

## Analysis
### Key Considerations:
- **User Requirements**: Smart lighting control based on occupancy detection.
- **System Constraints**: Hardware limitations, network bandwidth, processing power.
- **Performance Metrics**: Detection accuracy, response time, user satisfaction.

## Software Details
- **Backend Development**:
  - **Python**: Main programming language for backend logic.
  - **Flask**: Framework for web server communication with ESP32.
- **Mobile Application**:
  - **Flutter/Dart**: Interface for interacting with ESP32 and displaying occupancy data.
- **Deep Learning**:
  - **YOLOv8 Model**: Used for human detection.
  - **OpenCV**: For image processing and video manipulation.

## Hardware Details
Key hardware components include:
- **ESP32 Microcontroller**: Manages device communication.
- **Relay Modules**: Controls lighting based on occupancy data.
- **Camera**: Captures video for YOLOv8 processing.
- **LED Bulbs**: Primary lighting source, controlled by relays.
- **Breadboard and Wires**: For prototyping and connections.

## Design Details
- **System Architecture**:
  - Data Flow: Camera captures video, YOLOv8 processes data, and sends occupancy status to ESP32.
- **User Interface Design**:
  - Mobile App UI: For easy control of lights and viewing occupancy data.

## Troubleshooting
Steps taken during implementation:
- **Debugging Software**: Used tools and logs for code and data flow issues.
- **Hardware Testing**: Verified functionality of hardware components.
- **Iterative Improvements**: Tested individual components before full integration.

---

## Getting Started
### Prerequisites
- Python 3.x
- Flask
- OpenCV
- ESP32 microcontroller setup
- Flutter and Dart SDKs
