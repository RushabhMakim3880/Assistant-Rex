import pyaudio

p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

print(f"Host API: {info.get('name')}")
print(f"Total Devices: {numdevices}\n")

for i in range(0, numdevices):
    dev_info = p.get_device_info_by_host_api_device_index(0, i)
    name = dev_info.get('name')
    max_in = dev_info.get('maxInputChannels')
    max_out = dev_info.get('maxOutputChannels')
    default_rate = dev_info.get('defaultSampleRate')
    
    print(f"Device {i}: {name}")
    print(f"  Max Input Channels: {max_in}")
    print(f"  Max Output Channels: {max_out}")
    print(f"  Default Sample Rate: {default_rate}")
    
    if max_out > 0:
        # Test common sample rates
        rates = [24000, 44100, 48000]
        supported_rates = []
        for rate in rates:
            try:
                if p.is_format_supported(rate, output_device=i, output_channels=max_out, output_format=pyaudio.paInt16):
                    supported_rates.append(rate)
            except:
                pass
        print(f"  Supported Rates (at max out): {supported_rates}")
    print("-" * 30)

p.terminate()
