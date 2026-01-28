import pyaudio
import time
import math
import struct

def list_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("\n--- Available Audio Input Devices ---")
    input_devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print(f"Index {i}: {name}")
            input_devices.append(i)
    
    p.terminate()
    return input_devices

def test_microphone(device_index):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    
    print(f"\n--- Testing Microphone (Index {device_index}) ---")
    print("Please speak into the microphone for 5 seconds...")
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK)
        
        start_time = time.time()
        max_rms = 0
        
        while time.time() - start_time < 5:
            data = stream.read(CHUNK, exception_on_overflow=False)
            shorts = struct.unpack(f"<{len(data)//2}h", data)
            sum_squares = sum(s**2 for s in shorts)
            rms = math.sqrt(sum_squares / len(shorts))
            max_rms = max(max_rms, rms)
            
            bars = "#" * int(rms / 100)
            print(f"Level: {int(rms)} {bars}", end='\r')
            
        print(f"\nMax RMS observed: {int(max_rms)}")
        if max_rms < 100:
            print("WARNING: Input level is very low. Is the microphone muted or volume too low?")
        else:
            print("SUCCESS: Audio input detected.")
            
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"ERROR: Failed to open or read from device: {e}")
        
    p.terminate()

if __name__ == "__main__":
    devices = list_devices()
    if devices:
        print("\nUsing default device (or first available)...")
        # You might want to let the user pick, but for this non-interactive run we'll pick the default or 1st
        # Default is usually what PyAudio picks if index is None, but let's try to be explicit if needed.
        # Check default input device
        p = pyaudio.PyAudio()
        try:
            default_device = p.get_default_input_device_info()
            print(f"System Default Input Device: Index {default_device['index']} - {default_device['name']}")
            test_microphone(default_device['index'])
        except Exception as e:
            print(f"Could not get default device: {e}")
            if devices:
                test_microphone(devices[0])
        p.terminate()
    else:
        print("No input devices found!")
