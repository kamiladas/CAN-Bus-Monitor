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

///  printCANMessage(can_id, dlc, data, "UART");

  byte sndStat = CAN0.sendMsgBuf(can_id, 0, dlc, data);
  if (sndStat == CAN_OK) {
    Serial.println("Message Sent Successfully!");
  } else {
    Serial.println("Error Sending Message...");
  }
  Serial.println();
}
