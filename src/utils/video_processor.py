import subprocess
import os
import time

def enhance_video(input_path, output_path, options, upload_id, status_dict):
    """
    Enhance video quality using FFmpeg
    
    Args:
        input_path: Path to input video file
        output_path: Path to output enhanced video file
        options: Dictionary with enhancement options
        upload_id: Unique ID for tracking progress
        status_dict: Dictionary to update processing status
    """
    
    try:
        # Build FFmpeg command based on options
        cmd = ['ffmpeg', '-i', input_path, '-y']  # -y to overwrite output file
        
        # Video filters to apply
        filters = []
        
        # Upscaling
        scale_factor = options.get('scale', 2)
        if scale_factor > 1:
            # Get input video dimensions first
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_streams', input_path
            ]
            
            try:
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                import json
                probe_data = json.loads(probe_result.stdout)
                
                # Find video stream
                video_stream = None
                for stream in probe_data['streams']:
                    if stream['codec_type'] == 'video':
                        video_stream = stream
                        break
                
                if video_stream:
                    width = int(video_stream['width'])
                    height = int(video_stream['height'])
                    new_width = width * scale_factor
                    new_height = height * scale_factor
                    filters.append(f'scale={new_width}:{new_height}:flags=lanczos')
                    
            except Exception as e:
                # Fallback to simple scaling
                filters.append(f'scale=iw*{scale_factor}:ih*{scale_factor}:flags=lanczos')
        
        # Denoising
        if options.get('denoise', False):
            filters.append('hqdn3d=4:3:6:4.5')
        
        # Sharpening
        if options.get('sharpen', False):
            filters.append('unsharp=5:5:1.0:5:5:0.0')
        
        # Color enhancement
        if options.get('enhance_colors', False):
            filters.append('eq=contrast=1.1:brightness=0.02:saturation=1.2')
        
        # Add filters to command if any
        if filters:
            filter_string = ','.join(filters)
            cmd.extend(['-vf', filter_string])
        
        # Video codec and quality settings
        cmd.extend([
            '-c:v', 'libx264',  # Use H.264 codec
            '-preset', 'medium',  # Balance between speed and compression
            '-crf', '18',  # High quality (lower CRF = higher quality)
            '-c:a', 'aac',  # Audio codec
            '-b:a', '128k',  # Audio bitrate
            output_path
        ])
        
        # Update status
        status_dict[upload_id]['progress'] = 60
        status_dict[upload_id]['message'] = 'Processing video with FFmpeg...'
        
        # Execute FFmpeg command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor progress (simplified - FFmpeg progress parsing can be complex)
        progress_steps = [70, 80, 90, 95]
        step_index = 0
        
        while process.poll() is None:
            time.sleep(2)  # Check every 2 seconds
            if step_index < len(progress_steps):
                status_dict[upload_id]['progress'] = progress_steps[step_index]
                status_dict[upload_id]['message'] = f'Processing... {progress_steps[step_index]}%'
                step_index += 1
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f'FFmpeg error: {stderr}')
        
        # Verify output file exists and has content
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception('Output file was not created or is empty')
        
        status_dict[upload_id]['progress'] = 98
        status_dict[upload_id]['message'] = 'Finalizing...'
        
    except Exception as e:
        raise Exception(f'Video processing failed: {str(e)}')

def get_video_info(video_path):
    """Get basic information about a video file"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        return json.loads(result.stdout)
        
    except Exception as e:
        return {'error': str(e)}

def estimate_processing_time(input_path, options):
    """Estimate processing time based on video properties and options"""
    try:
        info = get_video_info(input_path)
        if 'error' in info:
            return 60  # Default estimate
        
        # Get video duration
        duration = float(info['format'].get('duration', 60))
        
        # Base processing time (seconds per minute of video)
        base_time = 30
        
        # Adjust based on options
        scale_factor = options.get('scale', 1)
        if scale_factor > 2:
            base_time *= 2
        elif scale_factor > 1:
            base_time *= 1.5
        
        if options.get('denoise', False):
            base_time *= 1.2
        
        if options.get('sharpen', False):
            base_time *= 1.1
        
        estimated_seconds = (duration / 60) * base_time
        return max(30, int(estimated_seconds))  # Minimum 30 seconds
        
    except Exception:
        return 60  # Default estimate

