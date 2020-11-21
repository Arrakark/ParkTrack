#include <SPI.h>
#include <LoRa.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>
#include <CRC32.h>


SoftwareSerial GPS_SERIAL(3,8); // RX, TX
TinyGPSPlus gps;

boolean runEvery(unsigned long interval);


void setup() {
  LoRa.setPins(10, 9, 2);
  if (!LoRa.begin(433E6)) {
    while (1);
  }
  LoRa.setTxPower(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setSpreadingFactor(12);
  GPS_SERIAL.begin(9600);
}

void loop() {
  while (GPS_SERIAL.available() > 0)
    gps.encode(GPS_SERIAL.read());

  if (runEvery(5000)) {
    LoRa.beginPacket();
    if (gps.location.isValid())
    {
      String output = String(gps.location.lat(), 6) + " " + String(gps.location.lng(), 6) + " " + String(gps.speed.kmph(), 1) + " ";

      CRC32 crc;

      for(auto x : output)
      {
        crc.update(x);
      }

      LoRa.print(output);
      LoRa.print(crc.finalize(), HEX);
    }
    else {
      if (millis() > 5000 && gps.charsProcessed() < 10)
      {
        LoRa.print("N GPS");
      }
      else {
        LoRa.print("No Lock");
      }
    }
    LoRa.endPacket(false);
  }
}

boolean runEvery(unsigned long interval)
{
  static unsigned long previousMillis = 0;
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval)
  {
    previousMillis = currentMillis;
    return true;
  }
  return false;
}