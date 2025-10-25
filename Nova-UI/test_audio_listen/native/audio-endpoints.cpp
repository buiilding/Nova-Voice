#include <napi.h>
#include <windows.h>
#include <mmdeviceapi.h>
#include <functiondiscoverykeys_devpkey.h>
#include <propvarutil.h>
#include <vector>
#include <string>

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")

class AudioEndpoints : public Napi::ObjectWrap<AudioEndpoints> {
private:
    IMMDeviceEnumerator* pEnumerator;

public:
    static Napi::Object Init(Napi::Env env, Napi::Object exports) {
        Napi::Function func = DefineClass(env, "AudioEndpoints", {
            InstanceMethod("enumerateEndpoints", &AudioEndpoints::EnumerateEndpoints),
        });

        exports.Set("AudioEndpoints", func);
        return exports;
    }

    AudioEndpoints(const Napi::CallbackInfo& info) : Napi::ObjectWrap<AudioEndpoints>(info), pEnumerator(nullptr) {
        CoInitialize(nullptr);
        HRESULT hr = CoCreateInstance(
            __uuidof(MMDeviceEnumerator),
            nullptr,
            CLSCTX_ALL,
            __uuidof(IMMDeviceEnumerator),
            (void**)&pEnumerator
        );
        if (FAILED(hr)) {
            throw Napi::Error::New(info.Env(), "Failed to create MMDeviceEnumerator");
        }
    }

    ~AudioEndpoints() {
        if (pEnumerator) {
            pEnumerator->Release();
        }
        CoUninitialize();
    }

    Napi::Value EnumerateEndpoints(const Napi::CallbackInfo& info) {
        Napi::Env env = info.Env();
        
        if (!pEnumerator) {
            throw Napi::Error::New(env, "MMDeviceEnumerator not initialized");
        }

        Napi::Array result = Napi::Array::New(env);
        int index = 0;

        // Enumerate capture (microphone) devices
        EnumerateDevices(env, result, index, eCapture, "capture");
        
        // Enumerate render (speaker) devices  
        EnumerateDevices(env, result, index, eRender, "render");

        return result;
    }

private:
    void EnumerateDevices(Napi::Env env, Napi::Array& result, int& index, EDataFlow flow, const std::string& flowType) {
        IMMDeviceCollection* pCollection = nullptr;
        HRESULT hr = pEnumerator->EnumAudioEndpoints(flow, DEVICE_STATE_ACTIVE, &pCollection);
        
        if (SUCCEEDED(hr)) {
            UINT deviceCount = 0;
            pCollection->GetCount(&deviceCount);
            
            for (UINT i = 0; i < deviceCount; i++) {
                IMMDevice* pDevice = nullptr;
                hr = pCollection->Item(i, &pDevice);
                
                if (SUCCEEDED(hr)) {
                    Napi::Object deviceObj = Napi::Object::New(env);
                    
                    // Get device ID
                    LPWSTR deviceId = nullptr;
                    hr = pDevice->GetId(&deviceId);
                    if (SUCCEEDED(hr)) {
                        std::wstring wDeviceId(deviceId);
                        deviceObj.Set("id", Napi::String::New(env, std::string(wDeviceId.begin(), wDeviceId.end())));
                        CoTaskMemFree(deviceId);
                    }
                    
                    // Get device friendly name (like Windows Settings)
                    IPropertyStore* pProps = nullptr;
                    hr = pDevice->OpenPropertyStore(STGM_READ, &pProps);
                    if (SUCCEEDED(hr)) {
                        PROPVARIANT varName;
                        PropVariantInit(&varName);
                        hr = pProps->GetValue(PKEY_Device_FriendlyName, &varName);
                        if (SUCCEEDED(hr) && varName.vt == VT_LPWSTR) {
                            std::wstring wName(varName.pwszVal);
                            deviceObj.Set("name", Napi::String::New(env, std::string(wName.begin(), wName.end())));
                        }
                        PropVariantClear(&varName);
                        pProps->Release();
                    }
                    
                    deviceObj.Set("flow", flowType);
                    deviceObj.Set("state", "active");
                    
                    result.Set(index++, deviceObj);
                    pDevice->Release();
                }
            }
            pCollection->Release();
        }
    }
};

Napi::Object Init(Napi::Env env, Napi::Object exports) {
    return AudioEndpoints::Init(env, exports);
}

NODE_API_MODULE(audio_endpoints, Init)
