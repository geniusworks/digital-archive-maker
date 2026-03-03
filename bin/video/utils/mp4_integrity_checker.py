#!/usr/bin/env python3
"""
MP4 Integrity Checker - Analyze MP4 files for encoding and streaming compatibility issues.
Automatically detects MP4 directories and outputs summary to stdout.
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

def run_command(cmd, capture=True, timeout=10):
    """Run a command and return result"""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
            return result
        else:
            subprocess.run(cmd, check=True)
            return None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None

def find_mp4_directories():
    """Find directories containing MP4 files in the library"""
    base_dirs = [
        Path("/Users/martin/Movies/Rips"),
        Path.home() / "Movies" / "Rips",
        Path("/Volumes/Data/Media/Library"),
    ]
    
    mp4_dirs = []
    
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
            
        # Look for directories with MP4 files
        for subdir in base_dir.rglob("*"):
            if subdir.is_dir():
                mp4_files = list(subdir.glob("*.mp4"))
                if mp4_files:
                    mp4_dirs.append((subdir, len(mp4_files)))
    
    return sorted(mp4_dirs, key=lambda x: x[1], reverse=True)  # Sort by file count

def analyze_file_encoding(mp4_path):
    """Analyze file for encoding issues"""
    issues = []
    info = {}
    
    # Get basic file info
    try:
        stat = mp4_path.stat()
        info['size_mb'] = round(stat.st_size / (1024 * 1024), 2)
    except:
        issues.append("Cannot read file stats")
        return issues, info
    
    # Use ffprobe to get detailed stream info
    cmd = [
        'ffprobe', '-v', 'error', '-show_format', '-show_streams',
        '-print_format', 'json', str(mp4_path)
    ]
    result = run_command(cmd)
    
    if not result or result.returncode != 0:
        issues.append("ffprobe failed to analyze file")
        return issues, info
    
    try:
        probe_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        issues.append("Invalid ffprobe output")
        return issues, info
    
    # Analyze format
    format_info = probe_data.get('format', {})
    info['duration'] = format_info.get('duration', 'unknown')
    info['bit_rate'] = format_info.get('bit_rate', 'unknown')
    info['format_name'] = format_info.get('format_name', 'unknown')
    
    # Analyze streams
    video_streams = []
    audio_streams = []
    
    for stream in probe_data.get('streams', []):
        codec_type = stream.get('codec_type', '')
        if codec_type == 'video':
            video_streams.append(stream)
        elif codec_type == 'audio':
            audio_streams.append(stream)
    
    info['video_count'] = len(video_streams)
    info['audio_count'] = len(audio_streams)
    
    # Check video stream issues
    if not video_streams:
        issues.append("No video streams found")
    else:
        video = video_streams[0]
        info['video_codec'] = video.get('codec_name', 'unknown')
        info['video_width'] = video.get('width', 'unknown')
        info['video_height'] = video.get('height', 'unknown')
        info['video_frame_rate'] = video.get('r_frame_rate', 'unknown')
        info['video_pixel_format'] = video.get('pix_fmt', 'unknown')
        
        # Check for problematic video settings
        if info['video_codec'] not in ['h264', 'hevc', 'avc', 'mpeg4']:
            issues.append(f"Unusual video codec: {info['video_codec']}")
        
        if info['video_pixel_format'] == 'yuv420p10le':
            issues.append("10-bit color depth may cause compatibility issues")
        elif info['video_pixel_format'] not in ['yuv420p', 'yuvj420p']:
            issues.append(f"Unusual pixel format: {info['video_pixel_format']}")
        
        # Check frame rate
        if info['video_frame_rate'] and info['video_frame_rate'] != 'unknown':
            try:
                num, den = map(int, info['video_frame_rate'].split('/'))
                fps = num / den if den != 0 else 0
                if fps > 60 or fps < 23.976:
                    issues.append(f"Unusual frame rate: {fps:.2f} fps")
            except:
                issues.append(f"Invalid frame rate: {info['video_frame_rate']}")
    
    # Check audio stream issues
    if not audio_streams:
        issues.append("No audio streams found")
    else:
        for i, audio in enumerate(audio_streams):
            codec = audio.get('codec_name', 'unknown')
            channels = audio.get('channels', 'unknown')
            
            if codec not in ['aac', 'ac3', 'eac3', 'mp3', 'dts', 'flac']:
                issues.append(f"Audio stream {i}: Unusual codec {codec}")
            
            # DTS can cause issues with some players
            if codec in ['dts', 'truehd']:
                issues.append(f"Audio stream {i}: {codec.upper()} may cause compatibility issues")
            
            if channels:
                if isinstance(channels, str) and channels.isdigit() and int(channels) > 8:
                    issues.append(f"Audio stream {i}: Too many channels ({channels})")
                elif isinstance(channels, (int, float)) and channels > 8:
                    issues.append(f"Audio stream {i}: Too many channels ({channels})")
    
    # Check for high bitrate issues
    if info['bit_rate'] and info['bit_rate'] != 'unknown':
        try:
            bitrate = int(info['bit_rate'])
            if bitrate > 20000000:  # 20 Mbps
                issues.append(f"Very high bitrate: {bitrate/1000000:.1f} Mbps")
        except:
            pass
    
    return issues, info

def analyze_streaming_compatibility(mp4_path, info):
    """Analyze file for streaming compatibility issues"""
    issues = []
    
    # Quick format check
    cmd = ['ffprobe', '-v', 'error', '-show_format', '-show_entries',
           'format=format_name,duration,size,bit_rate', '-of', 'json', str(mp4_path)]
    result = run_command(cmd)
    
    if not result or result.returncode != 0:
        issues.append("Cannot analyze file format")
        return issues
    
    try:
        data = json.loads(result.stdout)
        format_info = data.get('format', {})
        
        # Check format
        format_name = format_info.get('format_name', '')
        if 'mp4' not in format_name:
            issues.append(f"Non-MP4 format: {format_name}")
        
        # Check for basic consistency
        duration = float(format_info.get('duration', 0))
        size = int(format_info.get('size', 0))
        bitrate = int(format_info.get('bit_rate', 0))
        
        if duration > 0 and bitrate > 0 and size > 0:
            # Rough consistency check
            expected_size = duration * bitrate / 8
            if abs(expected_size - size) / size > 0.2:  # 20% difference
                issues.append("File size/bitrate inconsistency - may indicate corruption")
        
        # Check for very high bitrate
        if bitrate > 15000000:  # 15 Mbps
            issues.append(f"High bitrate for streaming: {bitrate/1000000:.1f} Mbps")
        
        # Check duration
        if duration < 60:  # Less than 1 minute
            issues.append(f"Very short duration: {duration:.1f} seconds")
        elif duration > 14400:  # More than 4 hours
            issues.append(f"Very long duration: {duration/3600:.1f} hours")
        
    except (json.JSONDecodeError, ValueError, KeyError):
        issues.append("Cannot parse file information")
    
    return issues

def analyze_mp4_file(mp4_path):
    """Complete analysis of a single MP4 file"""
    encoding_issues, info = analyze_file_encoding(mp4_path)
    streaming_issues = analyze_streaming_compatibility(mp4_path, info)
    
    all_issues = encoding_issues + streaming_issues
    
    return {
        'path': mp4_path,
        'encoding_issues': encoding_issues,
        'streaming_issues': streaming_issues,
        'all_issues': all_issues,
        'info': info
    }

def main():
    """Main analysis function"""
    import sys
    
    print("🔍 MP4 Integrity Checker")
    print("=" * 50)
    
    # Check if directory argument provided
    target_dir = None
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
        if not target_dir.exists():
            print(f"❌ Directory not found: {target_dir}")
            print("Usage: python3 mp4_integrity_checker.py [directory]")
            return
    else:
        # Auto-detect MP4 directories
        print("🔍 Scanning for MP4 directories...")
        mp4_dirs = find_mp4_directories()
        
        if not mp4_dirs:
            print("❌ No directories with MP4 files found")
            print("💡 Try specifying a directory: python3 mp4_integrity_checker.py /path/to/mp4s")
            return
        
        print(f"📁 Found {len(mp4_dirs)} directories with MP4 files:")
        for i, (dir_path, count) in enumerate(mp4_dirs[:5], 1):
            print(f"   {i}. {dir_path} ({count} files)")
        
        if len(mp4_dirs) > 1:
            print(f"   ... and {len(mp4_dirs) - 5} more directories")
            print()
            print("🎯 Using directory with most MP4 files")
        
        target_dir = mp4_dirs[0][0]
    
    print(f"🎬 Analyzing MP4 files in: {target_dir}")
    print()
    
    # Find all MP4 files
    mp4_files = list(target_dir.rglob("*.mp4"))
    
    if not mp4_files:
        print("❌ No MP4 files found")
        return
    
    print(f"📁 Found {len(mp4_files)} MP4 files...")
    print()
    
    # Analyze each file
    results = []
    for i, mp4_path in enumerate(sorted(mp4_files), 1):
        print(f"[{i:2d}/{len(mp4_files)}] 📄 {mp4_path.name}", end="", flush=True)
        
        result = analyze_mp4_file(mp4_path)
        results.append(result)
        
        if result['all_issues']:
            print(f" ⚠️  {len(result['all_issues'])} issues")
        else:
            print(" ✅")
    
    print()
    print("=" * 60)
    print("📊 INTEGRITY CHECK SUMMARY")
    print("=" * 60)
    
    # Summary statistics
    files_with_encoding_issues = [r for r in results if r['encoding_issues']]
    files_with_streaming_issues = [r for r in results if r['streaming_issues']]
    files_with_any_issues = [r for r in results if r['all_issues']]
    
    print(f"📈 Total files analyzed: {len(results)}")
    print(f"✅ Perfect files: {len(results) - len(files_with_any_issues)}")
    print(f"⚠️  Files with encoding issues: {len(files_with_encoding_issues)}")
    print(f"🌐 Files with streaming issues: {len(files_with_streaming_issues)}")
    print(f"📋 Files with any issues: {len(files_with_any_issues)}")
    print()
    
    if files_with_any_issues:
        print("🔍 DETAILED ISSUES:")
        print("-" * 40)
        
        for result in files_with_any_issues:
            print(f"📁 {result['path'].name}")
            
            if result['encoding_issues']:
                print("   🔧 Encoding issues:")
                for issue in result['encoding_issues']:
                    print(f"      ⚠️  {issue}")
            
            if result['streaming_issues']:
                print("   🌐 Streaming issues:")
                for issue in result['streaming_issues']:
                    print(f"      ⚠️  {issue}")
            
            print()
        
        # Common issues summary
        print("📋 MOST COMMON ISSUES:")
        print("-" * 30)
        
        all_issue_counts = {}
        encoding_issue_counts = {}
        streaming_issue_counts = {}
        
        for result in files_with_any_issues:
            for issue in result['encoding_issues']:
                encoding_issue_counts[issue] = encoding_issue_counts.get(issue, 0) + 1
                all_issue_counts[issue] = all_issue_counts.get(issue, 0) + 1
            
            for issue in result['streaming_issues']:
                streaming_issue_counts[issue] = streaming_issue_counts.get(issue, 0) + 1
                all_issue_counts[issue] = all_issue_counts.get(issue, 0) + 1
        
        for issue, count in sorted(all_issue_counts.items(), key=lambda x: x[1], reverse=True):
            category = "🔧" if issue in encoding_issue_counts else "🌐"
            print(f"   {category} {count}x: {issue}")
        
        print()
        print("💡 RECOMMENDATIONS:")
        print("-" * 25)
        
        if encoding_issue_counts:
            print("🔧 For encoding issues:")
            print("   • Re-encode with HandBrake using Fast 1080p30 preset")
            print("   • Use H.264 codec for maximum compatibility")
            print("   • Keep bitrate under 20 Mbps")
            print("   • Use standard frame rates (23.976, 24, 29.97, 30 fps)")
            print()
        
        if streaming_issue_counts:
            print("🌐 For streaming issues:")
            print("   • Enable Direct Play in Jellyfin settings")
            print("   • Check network bandwidth (min 10 Mbps)")
            print("   • Monitor server resources during playback")
            print("   • Check Jellyfin server logs for specific errors")
            print()
        
        print("🔧 General recommendations:")
        print("   • Test problematic files with VLC first")
        print("   • Consider batch re-encoding for consistency")
        print("   • Use MP4Box or ffmpeg for container optimization")
        
    else:
        print("🎉 All files have perfect integrity!")
        print("✨ No encoding or streaming issues detected")
        print()
        print("📝 Sample file details:")
        print("-" * 30)
        for result in results[:3]:
            info = result['info']
            print(f"📁 {result['path'].name}")
            print(f"   📹 {info.get('video_codec', '?')} ({info.get('video_width', '?')}x{info.get('video_height', '?')})")
            print(f"   💾 {info.get('size_mb', '?')} MB")
            print(f"   ⏱️  {info.get('duration', '?')} sec")
            print()
        
        if len(results) > 3:
            print(f"... and {len(results) - 3} more perfect files ✅")

if __name__ == "__main__":
    main()
