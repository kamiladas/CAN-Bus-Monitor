
# CAN Bus Monitor

## Project Overview

CAN Bus Monitor is an application designed for monitoring, analyzing, and sending CAN (Controller Area Network) frames via a serial port. The application allows connecting to a CAN bus, monitoring transmitted messages, recording data, and sending frames both individually and cyclically. The project is developed using Python and the Tkinter library for the graphical interface.

The main execution unit of the system is the ESP32 module connected to the MCP2515 CAN controller, which communicates with the CAN bus and sends data to the computer via the serial port.

This project offers a highly cost-effective alternative to professional CAN tools such as CanHacker, SavvyCAN, and PCAN-View. By leveraging affordable hardware like the ESP32 and MCP2515, this solution provides similar functionality at a fraction of the cost, making it accessible for hobbyists, developers, and small-scale automotive projects.

## Features

1. **Connecting to the CAN Bus**:
   - Selecting the COM port and baud rate.
   - Connecting to the CAN bus via the serial port.
   - The ESP32 module connected to the MCP2515 handles communication with the CAN bus and forwards data to the application.

![Connections](https://github.com/user-attachments/assets/77f69ed9-a83b-4fb3-8331-95b4874c83df)  <!-- Image placeholder -->

2. **CAN Data Monitoring and Analysis**:
   - Receiving CAN frames, displaying their ID, DLC (Data Length Code), data, the number of received frames, and the period (in ms).
   - Ability to reset monitoring statistics.

![CAN_monitor](https://github.com/user-attachments/assets/623f5616-f59b-41b5-94f1-5f9fb6c63d0d) <!-- Image placeholder -->

3. **Recording and Saving Data**:
   - Recording received CAN frames.
   - Saving data to a JSON file.
   - Playing back saved data and displaying it in the graphical interface.

   ![PlayRec_CAN](https://github.com/user-attachments/assets/2a86fcc4-89ae-435c-88f8-3b59e5afcb98)  <!-- Image placeholder -->

4. **Sending CAN Frames**:
   - Sending individual CAN frames (CAN Single Shot).
   - Sending frames cyclically with a specified frequency.
   - Editing and filtering frames before sending them.
   
  ![Can_SingleShoot](https://github.com/user-attachments/assets/422fa7f3-779c-4038-ba72-1b800b57b6cf)  <!-- Image placeholder -->

5. **Reverse Engineering**:
   - A tool for analyzing data variability in CAN frames.
   - Highlighting data changes with colors to facilitate the identification of variable bits.

 ![Reverse](https://github.com/user-attachments/assets/1c03f8fc-6834-42fb-b572-1ce3f3bc329a) <!-- Image placeholder -->

6. **COM Communication Logger**:
   - Recording and displaying raw data from the serial port.
   - Sending messages through the COM port directly from the application.

![ComLoger](https://github.com/user-attachments/assets/7f8b02a0-16bb-48de-87b3-6d5bfaefca3e)  <!-- Image placeholder -->

## ESP32 and MCP2515 Script

The ESP32 module works with the MCP2515 CAN controller to enable communication with the CAN bus. Below is an example of a simple Arduino (C++) script for the ESP32 that receives data from the CAN bus and sends it via the serial port:

```cpp
#include <mcp_can.h>
#include <SPI.h>

#define HSPI_SCK 14
#define HSPI_MISO 12
#define HSPI_MOSI 13
#define HSPI_SS 15

SPIClass hspi(HSPI);
long unsigned int rxId;
unsigned char len = 0;
unsigned char rxBuf[8];
char msgString[128];

#define CAN0_INT 21
MCP_CAN CAN0(5);

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, 17, 16);

  if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK)
    Serial.println("First MCP2515 initialized successfully!");
  else
    Serial.println("Error initializing first MCP2515...");

  CAN0.setMode(MCP_NORMAL);

  pinMode(CAN0_INT, INPUT);

  Serial.println("Receiving example for MCP2515 CAN0...");
  Serial2.println("Serial 2 initialized successfully");
}

void loop() {
  if (!digitalRead(CAN0_INT)) {
    readCANMessage(CAN0, rxId, len, rxBuf, "MCP0");
  }
  
  if (Serial.available() > 0) {
    String uartMsg = Serial.readStringUntil('\n');
    printReceivedUARTMessage(uartMsg.c_str());
  }
}

void readCANMessage(MCP_CAN& can, long unsigned int& id, unsigned char& length, unsigned char* buf, const char* mcpLabel) {
  can.readMsgBuf(&id, &length, buf);
  
  printCANMessage(id, length, buf, mcpLabel);
}

void printCANMessage(long unsigned int id, unsigned char length, unsigned char* buf, const char* mcpLabel) {
  if ((id & 0x80000000) == 0x80000000)
    sprintf(msgString, "T%08X%d", (id & 0x1FFFFFFF), length);
  else
    sprintf(msgString, "T%03X%d", id, length);

  Serial.print(msgString);

  if ((id & 0x40000000) == 0x40000000) {
    Serial.print("R");
  } else {
    for (byte i = 0; i < length; i++) {
      sprintf(msgString, "%02X", buf[i]);
      Serial.print(msgString);
    }
  }
  
  Serial.println();
}

void printReceivedUARTMessage(const char* frame) {
  if (frame[0] != 'T') {
    if (frame[0] == 'E') {
      return;
    } else {
      Serial.println("Invalid frame format");
      return;
    }
  }

  char idStr[4] = { frame[1], frame[2], frame[3], '\0' };
  unsigned long can_id = strtoul(idStr, NULL, 16);

  unsigned int dlc = frame[4] - '0';

  char dataStr[3] = { '\0', '\0', '\0' };
  unsigned char data[8] = {0};

  for (unsigned int i = 0; i < dlc; i++) {
    dataStr[0] = frame[5 + i * 2];
    dataStr[1] = frame[6 + i * 2];
    data[i] = (unsigned char) strtoul(dataStr, NULL, 16);
  }

  Serial.print("CAN ID: 0x");
  Serial.print(can_id, HEX);
  Serial.print(" DLC: ");
  Serial.print(dlc);
  Serial.print(" Data: ");
  for (unsigned int i = 0; i < dlc; i++) {
    Serial.print("0x");
    Serial.print(data[i], HEX);
    if (i < dlc - 1) Serial.print(" ");
  }
  Serial.println();

  printCANMessage(can_id, dlc, data, "UART");

  byte sndStat = CAN0.sendMsgBuf(can_id, 0, dlc, data);
  if (sndStat == CAN_OK) {
    Serial.println("Message Sent Successfully!");
  } else {
    Serial.println("Error Sending Message...");
  }
  Serial.println();
}

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
