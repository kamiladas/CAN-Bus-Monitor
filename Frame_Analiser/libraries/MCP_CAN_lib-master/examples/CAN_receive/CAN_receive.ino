// Definicje pinów dla VSPI
#define VSPI_SCK  18
#define VSPI_MISO 19
#define VSPI_MOSI 23
#define VSPI_CS   5   // Chip Select dla MCP2515 na VSPI
#define CAN1_INT  32  // Interrupt Pin dla MCP2515 na VSPI

#include <SPI.h>
#include <mcp_can.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

SPIClass vspi(VSPI);
MCP_CAN CAN1(&vspi, VSPI_CS);  // MCP2515 na VSPI

void readCAN(void* pvParameters) {
    MCP_CAN* can = (MCP_CAN*) pvParameters;
    long unsigned int rxId;
    unsigned char len;
    unsigned char rxBuf[8];
    int canIntPin = CAN1_INT;

    //Serial.begin(115200); // Initialize Serial for debugging

    for(;;) { // Loop forever
        if(!digitalRead(canIntPin)) { // If CAN interrupt pin is low, read receive buffer
            can->readMsgBuf(&rxId, &len, rxBuf); // Read data: len = data length, buf = data byte(s)

            // Print CAN message to Serial
            Serial.print("ID: ");
            Serial.print(rxId, HEX);
            Serial.print(" Len: ");
            Serial.print(len);
            Serial.print(" Data: ");
            for (int i = 0; i < len; i++) {
                Serial.print(rxBuf[i], HEX);
                Serial.print(" ");
            }
            Serial.println();

            // Send CAN message to Python script
            ///sendToPython(rxId, len, rxBuf);
        }
        vTaskDelay(pdMS_TO_TICKS(10)); // Rest for a while
    }
}

void sendToPython(long unsigned int id, unsigned char len, unsigned char *buf) {
    // Format message for Python script and send via Serial
    Serial.print("T");  // Start of CAN frame
    Serial.print(id, HEX);  // CAN ID
    Serial.print(len, HEX);  // Data length
    for (int i = 0; i < len; i++) {
        if (buf[i] < 0x10) Serial.print("0");  // Leading zero for single digit bytes
        Serial.print(buf[i], HEX);
    }
    Serial.println();  // End of frame
}

void setup() {
    Serial.begin(115200);

    // Inicjalizacja VSPI i MCP2515 na VSPI
    vspi.begin(VSPI_SCK, VSPI_MISO, VSPI_MOSI, VSPI_CS);
    if (CAN1.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) != CAN_OK) Serial.println("Error Initializing MCP2515 na VSPI...");

    // Ustawienie MCP2515 na tryb normalny
    CAN1.setMode(MCP_NORMAL);

    // Tworzenie zadań FreeRTOS
    xTaskCreate(readCAN, "Read VSPI CAN", 2048, &CAN1, 1, NULL);
}

void loop() {
  // Pusta pętla - logika została przeniesiona do zadań FreeRTOS
}
