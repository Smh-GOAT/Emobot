#include "asr.h"

namespace {
const char BASE64_TABLE[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
}

AsrClient::AsrClient() {
}

void AsrClient::connect() {
    // Qwen ASR is called over one-shot HTTPS requests, so no persistent socket is needed.
}

void AsrClient::disconnect() {
    // No persistent ASR connection to tear down.
}

void AsrClient::loop(int delay_time) {
    (void)delay_time;
}

void AsrClient::blink_loop(uint32_t color) {
    blink_led(color);
}

bool AsrClient::ASR() {
    asr_result = "";
    set_led(COLOR_RED, 10);

    if (strlen(api_url) == 0 || strlen(api_key) == 0 || strlen(model) == 0) {
        log_error("Qwen ASR config is incomplete. Please set ASR_API_URL, ASR_API_KEY, and ASR_MODEL.");
        return false;
    }

    if (!recordToWav()) {
        return false;
    }

    return transcribeWav();
}

bool AsrClient::recordToWav() {
    if (FFat.exists(ASR_AUDIO_FILE)) {
        FFat.remove(ASR_AUDIO_FILE);
    }

    File file = FFat.open(ASR_AUDIO_FILE, FILE_WRITE);
    if (!file) {
        log_error("Failed to open ASR audio file for writing");
        return false;
    }

    uint8_t placeholder_header[WAV_HEADER_SIZE] = {0};
    if (file.write(placeholder_header, WAV_HEADER_SIZE) != WAV_HEADER_SIZE) {
        log_error("Failed to write placeholder WAV header");
        file.close();
        return false;
    }

    const size_t max_samples = RECORD_TIME * sample_rate;
    size_t samples_recorded = 0;
    uint32_t pcm_bytes_written = 0;
    unsigned long silence_start_time = 0;
    bool is_silent = false;
    bool voice_detected = false;
    int16_t* buffer = new int16_t[BUFFER_SIZE];

    if (!buffer) {
        log_error("Failed to allocate ASR audio buffer");
        file.close();
        return false;
    }

    while (samples_recorded < max_samples) {
        size_t remaining = max_samples - samples_recorded;
        size_t samples_to_read = remaining < BUFFER_SIZE ? remaining : BUFFER_SIZE;

        record(buffer, samples_to_read);
        enhanceVoice(buffer, samples_to_read);

        size_t mean = calculate_mean(buffer, samples_to_read);
        if (mean > SOUND_THRESHOLD) {
            set_led(COLOR_RED, 100);
            voice_detected = true;
            is_silent = false;
            silence_start_time = 0;
        } else {
            set_led(COLOR_RED, 10);
            if (voice_detected) {
                if (!is_silent) {
                    is_silent = true;
                    silence_start_time = millis();
                } else if (millis() - silence_start_time > MAX_SILENCE_TIME * 1000) {
                    break;
                }
            } else if (samples_recorded > sample_rate * 3) {
                break;
            }
        }

        size_t bytes_to_write = samples_to_read * sizeof(int16_t);
        if (file.write((uint8_t*)buffer, bytes_to_write) != bytes_to_write) {
            log_error("Failed to write ASR audio samples");
            delete[] buffer;
            file.close();
            return false;
        }

        pcm_bytes_written += bytes_to_write;
        samples_recorded += samples_to_read;
    }

    delete[] buffer;

    if (!voice_detected || pcm_bytes_written == 0) {
        log_info("No speech detected, skipping ASR request");
        file.close();
        FFat.remove(ASR_AUDIO_FILE);
        return false;
    }

    file.seek(0);
    writeWavHeader(file, pcm_bytes_written);
    file.close();
    return true;
}

void AsrClient::writeWavHeader(File& file, uint32_t pcm_bytes) {
    uint8_t header[WAV_HEADER_SIZE] = {0};
    uint32_t chunk_size = 36 + pcm_bytes;
    uint32_t byte_rate = sample_rate * channel * bits / 8;
    uint16_t block_align = channel * bits / 8;

    memcpy(header, "RIFF", 4);
    header[4] = chunk_size & 0xFF;
    header[5] = (chunk_size >> 8) & 0xFF;
    header[6] = (chunk_size >> 16) & 0xFF;
    header[7] = (chunk_size >> 24) & 0xFF;
    memcpy(header + 8, "WAVEfmt ", 8);
    header[16] = 16;
    header[20] = 1;
    header[22] = channel & 0xFF;
    header[23] = (channel >> 8) & 0xFF;
    header[24] = sample_rate & 0xFF;
    header[25] = (sample_rate >> 8) & 0xFF;
    header[26] = (sample_rate >> 16) & 0xFF;
    header[27] = (sample_rate >> 24) & 0xFF;
    header[28] = byte_rate & 0xFF;
    header[29] = (byte_rate >> 8) & 0xFF;
    header[30] = (byte_rate >> 16) & 0xFF;
    header[31] = (byte_rate >> 24) & 0xFF;
    header[32] = block_align & 0xFF;
    header[33] = (block_align >> 8) & 0xFF;
    header[34] = bits & 0xFF;
    header[35] = (bits >> 8) & 0xFF;
    memcpy(header + 36, "data", 4);
    header[40] = pcm_bytes & 0xFF;
    header[41] = (pcm_bytes >> 8) & 0xFF;
    header[42] = (pcm_bytes >> 16) & 0xFF;
    header[43] = (pcm_bytes >> 24) & 0xFF;

    file.write(header, WAV_HEADER_SIZE);
}

String AsrClient::encodeWavAsDataUrl() {
    File file = FFat.open(ASR_AUDIO_FILE, FILE_READ);
    if (!file) {
        log_error("Failed to open recorded WAV file");
        return "";
    }

    const char* prefix = "data:audio/wav;base64,";
    size_t estimated_length = strlen(prefix) + (((file.size() + 2) / 3) * 4);
    String data_url;
    data_url.reserve(estimated_length);
    data_url = prefix;

    uint8_t buffer[768];
    uint8_t carry[2] = {0};
    size_t carry_len = 0;

    while (file.available()) {
        size_t bytes_read = file.read(buffer + carry_len, sizeof(buffer) - carry_len);
        size_t total = carry_len + bytes_read;
        size_t encode_len = total - (total % 3);

        for (size_t i = 0; i < encode_len; i += 3) {
            char block[5];
            block[0] = BASE64_TABLE[(buffer[i] >> 2) & 0x3F];
            block[1] = BASE64_TABLE[((buffer[i] & 0x03) << 4) | ((buffer[i + 1] >> 4) & 0x0F)];
            block[2] = BASE64_TABLE[((buffer[i + 1] & 0x0F) << 2) | ((buffer[i + 2] >> 6) & 0x03)];
            block[3] = BASE64_TABLE[buffer[i + 2] & 0x3F];
            block[4] = '\0';
            data_url += block;
        }

        carry_len = total - encode_len;
        if (carry_len > 0) {
            memcpy(carry, buffer + encode_len, carry_len);
            memcpy(buffer, carry, carry_len);
        }
    }

    if (carry_len == 1) {
        char block[5];
        block[0] = BASE64_TABLE[(buffer[0] >> 2) & 0x3F];
        block[1] = BASE64_TABLE[(buffer[0] & 0x03) << 4];
        block[2] = '=';
        block[3] = '=';
        block[4] = '\0';
        data_url += block;
    } else if (carry_len == 2) {
        char block[5];
        block[0] = BASE64_TABLE[(buffer[0] >> 2) & 0x3F];
        block[1] = BASE64_TABLE[((buffer[0] & 0x03) << 4) | ((buffer[1] >> 4) & 0x0F)];
        block[2] = BASE64_TABLE[(buffer[1] & 0x0F) << 2];
        block[3] = '=';
        block[4] = '\0';
        data_url += block;
    }

    file.close();
    return data_url;
}

bool AsrClient::transcribeWav() {
    String audio_data_url = encodeWavAsDataUrl();
    if (audio_data_url.isEmpty()) {
        return false;
    }

    String payload;
    payload.reserve(audio_data_url.length() + 256);
    payload = "{\"model\":\"";
    payload += model;
    payload += "\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":[{\"audio\":\"";
    payload += audio_data_url;
    payload += "\"}]}]},\"parameters\":{\"asr_options\":{\"language\":\"";
    payload += language;
    payload += "\",\"enable_itn\":";
    payload += (enable_itn ? "true" : "false");
    payload += "}}}";

    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;
    if (!http.begin(client, api_url)) {
        log_error("Failed to initialize Qwen ASR HTTP client");
        return false;
    }

    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", String("Bearer ") + api_key);
    http.setTimeout(20000);

    int http_response_code = http.POST(payload);
    if (http_response_code <= 0) {
        log_error("Qwen ASR HTTP request failed: %d", http_response_code);
        http.end();
        return false;
    }

    String response_body = http.getString();
    http.end();

    asr_result = parseResponse(response_body);
    if (FFat.exists(ASR_AUDIO_FILE)) {
        FFat.remove(ASR_AUDIO_FILE);
    }

    if (asr_result.isEmpty()) {
        log_error("Qwen ASR returned an empty transcript");
        return false;
    }

    log_info("ASR: %s", asr_result.c_str());
    return true;
}

String AsrClient::parseResponse(const String& jsonString) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, jsonString);
    if (error) {
        log_error("Failed to parse Qwen ASR response");
        return "";
    }

    if (doc["output"]["choices"].is<JsonArray>() && doc["output"]["choices"].size() > 0) {
        JsonArray content = doc["output"]["choices"][0]["message"]["content"].as<JsonArray>();
        if (content.size() > 0 && content[0]["text"].is<String>()) {
            return content[0]["text"].as<String>();
        }
    }

    if (doc["message"].is<String>()) {
        log_error("Qwen ASR error: %s", doc["message"].as<const char*>());
    } else {
        log_error("Unexpected Qwen ASR response format");
    }
    return "";
}

String AsrClient::asrResult() {
    return asr_result;
}
