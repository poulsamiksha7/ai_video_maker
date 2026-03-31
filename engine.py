import os

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

import whisper
import mysql.connector
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

def connect_db(db_config):
    return mysql.connector.connect(**db_config)

def apply_dynamic_zoom(clip, zoom_ratio=0.04):
    """Slowly zooms into the image over its duration."""
    return clip.resize(lambda t: 1 + zoom_ratio * t / clip.duration)

def render_video_task(video_id, job_dir, image_paths, audio_path, template_name, language_choice, enable_captions, output_folder, db_config):
    conn = connect_db(db_config)
    cursor = conn.cursor()
    print(f"[Engine] Starting job {video_id} | Template: {template_name} | Captions: {enable_captions}")
    
    try:
        # 1. Load Audio
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        TARGET_W, TARGET_H = 1080, 1920
        
        # 2. Optional Transcription (Only if user requested it)
        transcription_result = None
        if str(enable_captions).lower() == 'true':
            print(f"[Engine] AI Captions enabled. Transcribing...")
            model = whisper.load_model("base") 
            # Use chosen language or let it auto-detect
            lang = language_choice if language_choice else None
            transcription_result = model.transcribe(audio_path, word_timestamps=True, language=lang)
        else:
            print(f"[Engine] Skipping transcription as per user request.")

        # 3. Process Images
        num_images = len(image_paths)
        overlap = 1.0 if template_name == 'Cinematic Fade' and num_images > 1 else 0.0
        img_duration = (audio_duration + (num_images - 1) * overlap) / num_images
        
        clips = []
        for i, img_path in enumerate(image_paths):
            print(f"[Engine] Processing {os.path.basename(img_path)}")
            clip = ImageClip(img_path).set_duration(img_duration)
            
            # Aspect Ratio & Center Crop logic
            if (clip.w / clip.h) > (TARGET_W / TARGET_H):
                clip = clip.resize(height=TARGET_H) 
            else:
                clip = clip.resize(width=TARGET_W)  
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)
            
            # Apply Dynamic Zoom Effect
            if template_name == 'Dynamic Zoom':
                clip = apply_dynamic_zoom(clip)
            
            clips.append(clip)
            
        # 4. Assembly & Transitions
        if template_name == 'Cinematic Fade':
            video_clips = [clips[0]]
            for clip in clips[1:]:
                video_clips.append(clip.crossfadein(overlap))
            final_video = concatenate_videoclips(video_clips, padding=-overlap, method="compose")
        elif template_name == 'Dip to Black':
            final_video = concatenate_videoclips([c.fadein(0.5).fadeout(0.5) for c in clips], method="compose")
        else:
            final_video = concatenate_videoclips(clips, method="compose")
            
        final_video = final_video.set_audio(audio_clip)

        # 5. Generate Styled Captions (If enabled)
        text_clips = []
        if transcription_result:
            print(f"[Engine] Generating styled caption layers...")
            for segment in transcription_result.get('segments', []):
                for word_info in segment.get('words', []):
                    word = word_info['word'].strip().upper()
                    if not word: continue
                    
                    # Styled like CapCut
                    txt_clip = TextClip(
                        txt=word, 
                        fontsize=110, 
                        color='yellow', 
                        font=r"C:\Windows\Fonts\Nirmala.ttf",
                        stroke_color='black', 
                        stroke_width=3,
                        method='caption'
                    )
                    
                    txt_clip = txt_clip.set_position(('center', TARGET_H - 550))
                    txt_clip = txt_clip.set_start(word_info['start']).set_duration(word_info['end'] - word_info['start'])
                    text_clips.append(txt_clip)

        # 6. Composite & Render
        composite_video = CompositeVideoClip([final_video] + text_clips) if text_clips else final_video
        composite_video = composite_video.set_duration(audio_duration)

        output_filename = f"video_{video_id}.mp4"
        output_path = os.path.join(output_folder, output_filename)
        
        print(f"[Engine] Rendering final MP4: {output_filename}")
        composite_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast", 
            threads=4,          
            logger=None         
        )
        
        composite_video.close()
        audio_clip.close()
        
        # 7. Update Database
        cursor.execute("UPDATE videos SET status = 'done', video_path = %s WHERE id = %s", (output_filename, video_id))
        conn.commit()
        print(f"[Engine] Job {video_id} successful!")

    except Exception as e:
        print(f"[Engine] ERROR: {str(e)}")
        cursor.execute("UPDATE videos SET status = 'error' WHERE id = %s", (video_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()