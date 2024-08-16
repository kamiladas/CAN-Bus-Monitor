#include <mcp_can.h>
#include <SPI.h>

// Definicje pinów dla HSPI
#define HSPI_SCK 14
#define HSPI_MISO 12
#define HSPI_MOSI 13
#define HSPI_SS 15  // Możesz zmienić, jeśli używasz innego pinu dla CS

SPIClass hspi(HSPI);
long unsigned int rxId;
unsigned char len = 0;
unsigned char rxBuf[8];
char msgString[128]; // Tablica do przechowywania stringa do wysyłki przez UART

#define CAN0_INT 21 // Ustawienie INT na pin 21 dla pierwszego MCP2515
MCP_CAN CAN0(5); // Ustawienie CS na pin 5 dla pierwszego MCP2515

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, 17, 16);
  // Inicjalizacja UART2 z prędkością 115200

  // Inicjalizacja pierwszego MCP2515
  if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK)
    Serial.println("Pierwszy MCP2515 zainicjalizowany pomyślnie!");
  else
    Serial.println("Błąd inicjalizacji pierwszego MCP2515...");

  CAN0.setMode(MCP_NORMAL); // Ustawienie trybu operacyjnego na normalny dla pierwszego MCP2515

  pinMode(CAN0_INT, INPUT); // Konfiguracja pinu dla wejścia /INT dla pierwszego MCP2515

  Serial.println("Przykład odbierania dla MCP2515 CAN0...");
  Serial2.println("Serial 2 zainicjowany pomyślnie");
}

void loop() {
  // Sprawdzenie wiadomości na pierwszym MCP2515
  if (!digitalRead(CAN0_INT)) {
    readCANMessage(CAN0, rxId, len, rxBuf, "MCP0");
  }
  
  // Sprawdzenie wiadomości na UART
  if (Serial.available() > 0) {
    String uartMsg = Serial.readStringUntil('\n');
    printReceivedUARTMessage(uartMsg.c_str());
  }
}

void readCANMessage(MCP_CAN& can, long unsigned int& id, unsigned char& length, unsigned char* buf, const char* mcpLabel) {
  can.readMsgBuf(&id, &length, buf); // Odczyt danych: length = długość danych, buf = bajty danych
  
  // Wydrukuj szczegóły wiadomości z identyfikatorem MCP
  printCANMessage(id, length, buf, mcpLabel);
}

void printCANMessage(long unsigned int id, unsigned char length, unsigned char* buf, const char* mcpLabel) {
  if ((id & 0x80000000) == 0x80000000) // Określenie, czy ID jest standardowe czy rozszerzone
    sprintf(msgString, "T%08X%d", (id & 0x1FFFFFFF), length);
  else
    sprintf(msgString, "T%03X%d", id, length);

  Serial.print(msgString);

  if ((id & 0x40000000) == 0x40000000) { // Określenie, czy wiadomość jest ramką zdalną.
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
  // Sprawdzenie, czy ramka zaczyna się od 'T'
  if (frame[0] != 'T') {
    // Sprawdzenie, czy ramka to "END"
    if (frame[0] == 'E') {
      return; // Ignoruj komunikat "END"
    } else {
      Serial.println("Invalid frame format");
      return;
    }
  }

  // Wydobycie ID ramki (3 znaki w formacie 16-bitowym)
  char idStr[4] = { frame[1], frame[2], frame[3], '\0' };
  unsigned long can_id = strtoul(idStr, NULL, 16);

  // Wydobycie DLC (1 znak w formacie 16-bitowym)
  unsigned int dlc = frame[4] - '0';

  // Wydobycie danych (pozostałe znaki, po dwa znaki na bajt)
  char dataStr[3] = { '\0', '\0', '\0' };
  unsigned char data[8] = {0};

  for (unsigned int i = 0; i < dlc; i++) {
    dataStr[0] = frame[5 + i * 2];
    dataStr[1] = frame[6 + i * 2];
    data[i] = (unsigned char) strtoul(dataStr, NULL, 16);
  }

  // Wypisanie zdekodowanej ramki CAN
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

  // Zakodowanie ramki CAN i wyświetlenie jej w konsoli

  printCANMessage(can_id, dlc, data, "UART");    ///single shoot EMULATOR 

  // Wysyłanie wiadomości przez CAN
  byte sndStat = CAN0.sendMsgBuf(can_id, 0, dlc, data);
  if (sndStat == CAN_OK) {
    Serial.println("Message Sent Successfully!");
  } else {
    Serial.println("Error Sending Message...");
  }
  Serial.println(); // Dodanie pustej linii po informacji o wysłaniu
}
