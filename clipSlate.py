import os
import shutil
from time import strftime, gmtime
import subprocess
from PIL import Image, ImageDraw, ImageFont
import tempfile

# ===== SETUP
temp_dir = tempfile.TemporaryDirectory()
print(f"Temp Dir: {temp_dir.name}")
clip_path = "/Users/tcconway/Documents/GitHub/iw-clipSlate/_tests/test-videos/720p.mp4"
clip_dir = os.path.dirname(clip_path)
clip_name, clip_ext = os.path.splitext(os.path.basename(clip_path))

print('\nclipSlate')
print('---------')
print('v1.0, by TC Conway, IW Studios\n')
    
def get_clip_info(video):
    print(f'[clipSlate] Getting info on {clip_name}{clip_ext}...', end='')
    cmd = 'ffprobe -v error -select_streams v -count_packets -show_entries stream=width,height,duration,nb_read_packets,r_frame_rate -of csv=p=0 ' + video
    cmd_result = subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL).rstrip().decode('UTF-8')
    result = cmd_result.split(',')
    clip_width = int(result[0])
    clip_height = int(result[1])
    clip_framerate = result[2]
    clip_trt = float(result[3])
    clip_frames  = int(result[4])
    min_sec = strftime("%Mm%Ss", gmtime(clip_trt))
    print('DONE')
    return {'width':clip_width, 'height': clip_height, 'framerate':clip_framerate, 'frames':clip_frames, 'trt': clip_trt,'min_sec':min_sec,}


def extract_images(video,dur,segment_length):
    print("[clipSlate] Grabbing images from clip...", end='')
    img_to_extract = ''
    for x in range(100, dur, segment_length):
        img_to_extract += '+eq(n\\,' + str(x) + ')'
    cmd = 'ffmpeg -i ' + video + ' -vf select="' + img_to_extract + '" -vsync 0 "' + temp_dir.name + '/' + clip_name + '_%d.jpg"'
    dur = subprocess.run(cmd,shell=True,stderr=subprocess.DEVNULL)
    print("DONE")

def make_slate_1():
    # Note, this builds it as a 1920x1080, then resizes it at the end.
    slate = Image.new("RGB", (1920,1080), (0,0,0)).convert("RGBA")

    # Extract Images
    tot_stills = 6
    segment_length = int(clip_info["frames"] / tot_stills)
    extract_images(clip_path,clip_info["frames"],segment_length)

    # compile thumbnails
    print("[clipSlate] Compiling clipSlate image...", end='')
    imgs_path = []
    paste_coords = ((0, 360), (640, 360), (1280, 360), (0, 720), (640, 720), (1280, 720))

    for x in range(0,tot_stills):
        tmpImg = Image.open(temp_dir.name + '/' + clip_name + '_' + str(x+1) + '.jpg')
        tmpResized = tmpImg.resize((640,360))
        slate.paste(tmpResized,paste_coords[x])

    print("DONE")

    # add text
    print("[clipSlate] Adding text...", end='')
    font_label = ImageFont.truetype('Arial Narrow.ttf', 50)
    font_title = ImageFont.truetype('Arial Narrow.ttf', 85)
    font_trt = ImageFont.truetype('Arial Narrow.ttf', 250)
    title_linebreaked = insert_newlines(clip_name)
    if len(title_linebreaked) > 89:
        title_linebreaked = title_linebreaked[:92] +'...'
    draw = ImageDraw.Draw(slate)
    draw.text((96, 45), "title", font=font_label, fill='#666666')
    draw.text((1786, 45), "trt", font=font_label, fill='#666666')
    draw.text((1099, 52), clip_info["min_sec"], font=font_trt,fill='#FFBD00')
    draw.text((96, 88), title_linebreaked, font = font_title, fill='#CDCDCD')

    # Add Watermark
    txt_image = Image.new('RGBA', (1920,1080), (255,255,255,0))
    draw_text = ImageDraw.Draw(txt_image) 
    font_madewith = ImageFont.truetype('Arial.ttf', 15)
    font_clipslate = ImageFont.truetype('Arial.ttf', 35)
    draw_text.text((1760, 1000), "made with", font=font_madewith,  fill='#ffffff20')
    draw_text.text((1760, 1010), "clipSlate", font=font_clipslate, fill='#ffffff10')
    final_slate = Image.alpha_composite(slate, txt_image) 
    
    # Resize to the final video size
    final_slate.thumbnail((clip_info["width"], clip_info["height"]))
    final_slate = final_slate.convert("RGB")
    
    # Save
    slate_path = f'{clip_dir}/{clip_name}_slate.jpg'
    final_slate.save(slate_path, quality=95)
    print("DONE")

    # Insert into video
    print("[clipSlate] Transcoding video (this might take a while)...", end='')
    cmd = f'ffmpeg -y -i {clip_path} -i {slate_path} -filter_complex "overlay=0:0:enable=\'between(t,0,.01)\'" -preset fast -c:a copy {clip_dir}/{clip_name}_clipslate{clip_ext}'
    cmd_result = subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL)
    print("DONE")

def insert_newlines(string, every=30):
    return '\n'.join(string[i:i+every] for i in range(0, len(string), every))

# ----- Get video info
clip_info = get_clip_info(clip_path)
# Returns: clip_info[variable]  variables: width, height, framerate, frames, trt, min_sec

# ----- Make slate1
make_slate_1()

# ----- Insert into video


# ----- Clean up
temp_dir.cleanup()