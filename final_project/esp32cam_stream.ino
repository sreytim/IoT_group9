/*
 * LightControl — ESP32-CAM Stream Server
 * =======================================
 * Board  : AI Thinker ESP32-CAM
 * Port   : Stream at http://YOUR_IP/stream  (port 80)
 *
 * HOW TO UPLOAD:
 *   1. Open this file in Arduino IDE
 *   2. Fill in your WiFi SSID and password below
 *   3. Tools → Board → AI Thinker ESP32-CAM
 *   4. Tools → Port → select your COM port
 *   5. Click Upload (the board auto-resets into flash mode)
 *   6. After "Done uploading" → open Serial Monitor at 115200 baud
 *   7. Note the IP address printed — paste it into gesture_server.py
 *
 * FOLDER STRUCTURE (important!):
 *   esp32cam_stream/
 *   └── esp32cam_stream.ino   ← this file, alone in its own folder
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ── WiFi credentials ──────────────────────────────────────────
// !! CHANGE THESE to your actual WiFi name and password !!
const char* WIFI_SSID = "LikeaM";
const char* WIFI_PASS = "011666928me";

// ── AI Thinker ESP32-CAM pin definitions ─────────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ── MJPEG stream setup ────────────────────────────────────────
#define PART_BOUNDARY "lightcontrol_boundary"
static const char* STREAM_CONTENT_TYPE =
  "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY =
  "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART =
  "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;

// ── Stream handler — sends MJPEG frames continuously ─────────
static esp_err_t stream_handler(httpd_req_t* req) {
  camera_fb_t* fb  = NULL;
  esp_err_t    res = ESP_OK;
  char         part_buf[64];

  res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  // Disable timeout so stream stays open
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[CAM] Frame capture failed");
      res = ESP_FAIL;
      break;
    }

    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, fb->len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
    }

    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;
  }
  return res;
}

// ── Start HTTP server on port 80 ──────────────────────────────
void startStreamServer() {
  httpd_config_t config  = HTTPD_DEFAULT_CONFIG();
  config.server_port     = 80;
  config.ctrl_port       = 32768;
  config.max_uri_handlers = 4;

  httpd_uri_t stream_uri = {
    .uri      = "/stream",
    .method   = HTTP_GET,
    .handler  = stream_handler,
    .user_ctx = NULL
  };

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    Serial.println("[SERVER] Stream server started!");
  } else {
    Serial.println("[SERVER] Failed to start stream server");
  }
}

// ── Setup ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n=============================");
  Serial.println("  LightControl ESP32-CAM");
  Serial.println("=============================");

  // -- Camera configuration --
  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
  config.pin_sccb_sda  = SIOD_GPIO_NUM;
  config.pin_sccb_scl  = SIOC_GPIO_NUM;
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;
  config.xclk_freq_hz  = 20000000;
  config.pixel_format  = PIXFORMAT_JPEG;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location   = CAMERA_FB_IN_PSRAM;

  // Use QVGA for gesture detection — smaller = faster stream
  if (psramFound()) {
    config.frame_size   = FRAMESIZE_VGA;  // 640x480
    config.jpeg_quality = 10;
    config.fb_count     = 2;
    config.grab_mode    = CAMERA_GRAB_LATEST;
    Serial.println("[CAM] PSRAM found — using VGA (640x480)");
  } else {
    config.frame_size   = FRAMESIZE_QVGA; // 320x240
    config.jpeg_quality = 12;
    config.fb_count     = 1;
    config.fb_location  = CAMERA_FB_IN_DRAM;
    Serial.println("[CAM] No PSRAM — using QVGA (320x240)");
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init FAILED: 0x%x — check wiring!\n", err);
    return;
  }
  Serial.println("[CAM] Camera initialized OK");

  // Improve image quality
  sensor_t* s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_QVGA);  // Force QVGA for speed
  s->set_quality(s, 12);
  s->set_brightness(s, 1);

  // -- Connect to WiFi --
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  WiFi.setSleep(false);
  Serial.print("[WiFi] Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected!");

  startStreamServer();

  // Print the URL to paste into gesture_server.py
  Serial.println("\n=============================");
  Serial.print("  Stream URL: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");
  Serial.println("  Paste this into gesture_server.py");
  Serial.println("=============================\n");
}

// ── Loop — server runs in background, nothing to do here ─────
void loop() {
  delay(10000);
}
