
# CAN Bus Monitor

## Project Overview

CAN Bus Monitor is an application designed for monitoring, analyzing, and sending CAN (Controller Area Network) frames via a serial port. The application allows connecting to a CAN bus, monitoring transmitted messages, recording data, and sending frames both individually and cyclically. The project is developed using Python and the Tkinter library for the graphical interface.

The main execution unit of the system is the **ESP32** module connected to the **MCP2515** CAN controller, which communicates with the CAN bus and sends data to the computer via the serial port.

## Features

1. **Connecting to the CAN Bus**:
   - Selecting the COM port and baud rate.
   - Connecting to the CAN bus via the serial port.
   - The ESP32 module connected to the MCP2515 handles communication with the CAN bus and forwards data to the application.

   ![Connection Diagram](./Connections.PNG)  <!-- Image placeholder -->

2. **CAN Data Monitoring and Analysis**:
   - Receiving CAN frames, displaying their ID, DLC (Data Length Code), data, the number of received frames, and the period (in ms).
   - Ability to reset monitoring statistics.

   ![CAN Bus Monitor](./CAN_monitor.PNG)  <!-- Image placeholder -->

3. **Recording and Saving Data**:
   - Recording received CAN frames.
   - Saving data to a JSON file.
   - Playing back saved data and displaying it in the graphical interface.

   ![CAN Data Playback](./PlayRec_CAN.PNG)  <!-- Image placeholder -->

4. **Sending CAN Frames**:
   - Sending individual CAN frames (CAN Single Shot).
   - Sending frames cyclically with a specified frequency.
   - Editing and filtering frames before sending them.
   
   ![CAN Single Shot](./Can_SingleShoot.PNG)  <!-- Image placeholder -->

5. **Reverse Engineering**:
   - A tool for analyzing data variability in CAN frames.
   - Highlighting data changes with colors to facilitate the identification of variable bits.

   ![Reverse Engineering](./Reverse.PNG)  <!-- Image placeholder -->

6. **COM Communication Logger**:
   - Recording and displaying raw data from the serial port.
   - Sending messages through the COM port directly from the application.

   ![COM Logger](./ComLoger.PNG)  <!-- Image placeholder -->

## ESP32 and MCP2515 Script

The ESP32 module works with the MCP2515 CAN controller to enable communication with the CAN bus. Below is an example of a simple Arduino (C++) script for the ESP32 that receives data from the CAN bus and sends it via the serial port:

```cpp
// ESP32 and MCP2515 code
```

## System Requirements

- Python 3.6 or later.
- Installed libraries: `pyserial`, `tkinter`.
- Operating system with serial port support (Windows, Linux, macOS).

## Usage Instructions

1. **Connection Configuration**:
   - Launch the application and select the appropriate COM port and baud rate from the list.
   - Click "Connect" to establish a connection to the CAN bus.

2. **Data Monitoring**:
   - Once connected, the received CAN frames will be displayed in the main application window.
   - Use the "Reset Stats" button to clear the displayed statistics.

3. **Recording and Playing Data**:
   - To start recording data, click "Start Recording". Stop recording using "Stop Recording".
   - To save the recorded data, use "Save Recording". The file will be saved in JSON format.
   - To play back saved data, use "Play Recording" and select the appropriate file.

4. **Sending CAN Frames**:
   - Click "CAN Single Shot" to open the frame sending window. You can add new frames, edit existing ones, and send them to the CAN bus.
   - Use the "Start Periodic Send" option to send frames cyclically at a specified frequency.

5. **Data Variability Analysis**:
   - Use "Reverse Engineering" to open the tool for analyzing data variability in CAN frames.
   - Changing data bits are highlighted with colors, making them easier to identify.

6. **COM Communication Logger**:
   - Use "COM Logger" to open the communication logging window via the COM port.
   - You can also send raw data through the COM port directly from this window.

## Installation Instructions

1. Clone the repository to your computer:
   ```
   git clone <URL>
   cd CAN-Bus-Monitor
   ```

2. Install the required libraries:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
