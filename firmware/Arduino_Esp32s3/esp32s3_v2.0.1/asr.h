#ifndef ASR_H
#define ASR_H

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "common.h"
#include "audio.h"
#include "act.h"

#define MAX_WAIT_TIME 10
#define RECORD_TIME 10
#define MAX_SILENCE_TIME 2
#define BUFFER_SIZE (8 * 1024)
#define WAV_HEADER_SIZE 44
#define ASR_AUDIO_FILE "/asr_input.wav"

class AsrClient {

public:
    String asrResult();
    AsrClient();
    void connect();
    void disconnect();
    void loop(int delay_time = 100);
    bool ASR();

private:
    const char* api_url = ASR_API_URL;
    const char* api_key = ASR_API_KEY;
    const char* model = ASR_MODEL;
    const int sample_rate = 16000;
    const int bits = 16;
    const int channel = 1;
    const char* language = "zh";
    const bool enable_itn = false;
    String asr_result = "";

    bool recordToWav();
    bool transcribeWav();
    void blink_loop(uint32_t color = COLOR_BLUE);
    void writeWavHeader(File& file, uint32_t pcm_bytes);
    String encodeWavAsDataUrl();
    String parseResponse(const String& jsonString);
};

#endif
