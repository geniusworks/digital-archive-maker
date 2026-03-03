# Example: Small Box Media Server & Jellyfin Setup

*This document serves as a template and reference for a "Small Box" media server setup. It covers hardware, networking, and specific Jellyfin configurations optimized for low-power or small-form-factor devices.*

## 1. Hardware & Environment
*Describe the physical server and base operating system here.*

- **Device / Model**: (e.g., Beelink, Intel NUC, Raspberry Pi)
- **CPU**: (e.g., Intel N100)
- **RAM**: (e.g., 16GB DDR5)
- **Storage (OS)**: (e.g., 500GB NVMe M.2)
- **Storage (Media)**: (e.g., External 14TB USB 3.0 HDD)
- **Operating System**: (e.g., Debian 12, Ubuntu Server, macOS, Windows 11 Pro)

## 2. Networking & Remote Access
*How is the server exposed securely to the internet?*

- **Domain / DNS**: (e.g., `media.yourdomain.com`)
- **Proxy / Tunnel**: (e.g., Cloudflare Tunnel / cloudflared, Nginx Proxy Manager, Traefik)
- **SSL / HTTPS**: (e.g., Cloudflare Origin Certificate, Let's Encrypt)
- **Security / Access Control**: (e.g., Cloudflare Access, local network only, tailscale)

## 3. Jellyfin Installation
*How is Jellyfin running on the box?*

- **Deployment Method**: (e.g., Docker Compose, Bare Metal apt package, Windows Installer)
- **Version**: (e.g., 10.9.x)
- **Hardware Acceleration (Important for Small Boxes)**: 
  - *Method*: (e.g., Intel QuickSync (QSV), VAAPI, AMD AMF)
  - *Setup Notes*: (e.g., Passed `/dev/dri/renderD128` to docker container)

## 4. Jellyfin Configuration (Settings Summary)

### Dashboard > Playback (Transcoding)
*Optimizing playback so the small CPU doesn't choke on 4K/HEVC files.*

- **Hardware Acceleration**: (e.g., Intel QuickSync)
- **Enable hardware decoding for**: (Check H264, HEVC, AV1, VP9, etc.)
- **Enable hardware encoding**: (e.g., Checked)
- **Allow encoding in HEVC format**: (e.g., Checked if supported)
- **Throttle Transcoding**: (e.g., Checked - saves power when buffer is full)

### Dashboard > Libraries
*How the digital library is structured inside Jellyfin.*

- **Movies**: 
  - *Path*: `/media/Video/Movies`
  - *Scrapers*: TMDB, OMDB
  - *Settings*: NFO saving enabled, Chapter image extraction enabled (or disabled for CPU savings)
- **TV Shows**: 
  - *Path*: `/media/Video/TV Shows`
  - *Scrapers*: TMDB
- **Music**: 
  - *Path*: `/media/Audio/Music`
  - *Scrapers*: MusicBrainz

### Dashboard > Scheduled Tasks
*Tweaking background tasks to run at night so they don't interrupt viewing.*

- **Scan Media Library**: (e.g., Every 12 hours)
- **Extract Chapter Images**: (e.g., Run during off-hours, 2 AM - 6 AM, as it is CPU intensive)

### Dashboard > Plugins
*Useful plugins installed.*

- **1.** 
- **2.** 

---

## 5. Notes & Future Improvements
*Record any quirks, maintenance tasks, or planned upgrades here.*

- (e.g., "Need to set up a cron job to backup the Jellyfin database weekly.")
- (e.g., "Monitor temperature during 4K transcodes.")
