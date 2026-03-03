# Jellyfin Settings – Direct Play Optimized for Bmax Mini PC

This document outlines the specific Jellyfin settings used on a Bmax Mini PC. The primary goal of this configuration is to prioritize **Direct Play** and avoid CPU-intensive transcoding whenever possible, ensuring smooth playback on lower-power hardware.

## General Playback / Transcoding
*These settings ensure the CPU is not overwhelmed by attempting to transcode high-resolution or complex codecs.*

- **Hardware Acceleration:** None
- **Transcoding:** Off / None
- **Max Simultaneous Transcodes:** 1
- **Transcoding Thread Count:** 2
- **Encoding Preset (x264/x265):** veryfast (or superfast/ultrafast for lighter CPU load)
- **H.264 CRF:** 23 (optional: 25–26 for lower CPU load)
- **H.265 (HEVC) CRF:** 28
- **Allow encoding in HEVC format:** Unchecked
- **Allow encoding in AV1 format:** Unchecked
- **VBR Audio Encoding:** Unchecked
- **Audio Boost when Downmixing:** Default (2) or ignore
- **Stereo Downmix Algorithm:** None
- **Deinterlacing Method:** None (optional: YADIF if needed)
- **Double Frame Rate when Interlacing:** Off
- **Tone Mapping Algorithm:** None
- **Tone Mapping Range:** n/a (irrelevant with no tone mapping)

## Subtitles
*Subtitle rendering can cause unexpected transcoding; these settings minimize that risk.*

- **Enable fallback fonts:** Checked
- **Allow subtitle extraction on the fly:** Checked
- **Automatically Enable Subtitles:** Optional / off for Direct Play
- **Preferred Subtitle Language:** Set to your desired language

## Muxing / Segments
*Buffer and segment management.*

- **Max Muxing Queue Size:** 2048
- **Delete Segments:** On
- **Throttle Transcodes:** Off
- **Throttle After:** 180 (ignored, throttling off)
- **Time to Keep Segments:** 720 seconds (default)

## Notes & Philosophy
- These settings prioritize **Direct Play**, avoiding CPU-intensive transcoding whenever possible.
- HEVC/AV1 and subtitle rendering are left off or minimal to reduce CPU load.
- Fallback transcoding is rare; thread count and encoding presets are tuned to prevent overloading the CPU.
