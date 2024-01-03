import os
from os.path import isfile, join
import sys
import argparse
import time
import subprocess
from PIL import Image, ImageDraw, ImageFont
import tempfile
import filetype

#pyinstaller clipSlate.py -F --name "clipSlate" --clean

def show_header():
    print(f'{color.BOLD}clipSlate')
    print(f'v0.0.2 Alpha, by TC Conway, IW Studios{color.END}\n')
    print(f'{color.ITALIC}Disclaimer: Use of this program is at Your Own Risk\n')
    print('This program is provided "as is" without any warranties, express or implied, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose. The entire risk as to the quality and performance of the program is with you. Should the program prove defective, you assume the cost of all necessary servicing, repair, or correction.\n')
    print('In no event will TC Conway nor IW Studios LLC be liable to you or any third party for any damages, including any lost profits, lost savings or other incidental, consequential, or special damages arising out of the use of or inability to use this program, even if TC Conway or IW Studios LLC has been advised of the possibility of such damages.\n')
    print(f'By using this program, you acknowledge and agree to the terms of this disclaimer. If you do not agree to these terms, you may not use this program.{color.END}\n')

def path_type(path):
    # Checks if path is a file
    if os.path.isfile(path):
        return 'file'
    if os.path.isdir(path):
        return "dir"
    return 'not-valid'

def clean_path(path):
    cleaned_path = path.replace("\\ ", " ")
    cleaned_path = cleaned_path.strip("\'") # removes ' from beginning and end
    cleaned_path = cleaned_path.strip('\"') # removes "" from beginning and end
    cleaned_path = cleaned_path.strip() # removes outside spaces
    cleaned_path = os.path.abspath(path)
    return cleaned_path

def is_video(file):
    kind = filetype.guess(file)
    if kind:
        if kind.mime[:5] == "video":
            return True
        return False

def tell_user(msg = '',type = ''):
    if type.lower() == "clip":
        print(f'{color.CYAN}{msg}{color.END}')
    elif type.lower() == "alert":
        print(f'{color.YELLOW}[NOTE]{color.END} {msg}')
    elif type.lower() == "warn":
        print(f'{color.RED}[WARN] {msg}{color.END}')
    elif type.lower() == "success":
        print(f'{color.GREEN}[DONE]{color.END} {msg}\n')
    else:
        print(f'{color.BOLD}[INFO]{color.END} {msg}')

def debug(msg):
    print(f'{color.PURPLE}DEBUG: {msg}{color.END}')
    
def get_clip_paths_from_dir(dir):
    file_list = [f for f in os.listdir(dir) if isfile(os.path.join(dir, f))]

    clip_list = []
    for file in file_list:
        file = os.path.join(dir,file)
        if is_video(file):
            if '_clipslate' not in file :
                clip_list.append(file)
    return clip_list

def process_clip(file):
    if is_video(file):
        tell_user(file,'clip')
        # ===== Get clip info
        clip_name, clip_ext = os.path.splitext(os.path.basename(file))
        
        cmd = 'ffprobe -v error -select_streams v -count_packets -show_entries stream=codec_name,width,height,duration,nb_read_packets,r_frame_rate -of csv=p=0 "' + file + '"'

        try:
            cmd_result = subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL).rstrip().decode('UTF-8')
        except subprocess.CalledProcessError as e:
            print('Please install ffmpeg + ffprobe. See: https://ffmpeg.org/download.html\n\n')
            shutdown()

        result = cmd_result.split(',')

        clip_trt = float(result[4])
        min_sec = time.strftime("%Mm%Ss", time.gmtime(clip_trt))
        directory = clean_path(os.path.dirname(file))
        
        clip = {
            'name':         clip_name,
            'ext':          clip_ext,
            'path':         file,
            'directory':    directory,
            'codec':        result[0],
            'width':        int(result[1]),
            'height':       int(result[2]),
            'framerate':    result[3],
            'trt':          clip_trt,
            'frames':       int(result[5]),
            'min_sec':min_sec
            }


        # ===== Make Slate
        # Note, this builds it as a 1920x1080, then resizes it at the end.
        slate = Image.new("RGB", (1920,1080), (0,0,0)).convert("RGBA")

        # Extract Images
        tell_user('Grabbing thumbnails')
        tot_stills = 6
        segment_length = int(clip["frames"] / tot_stills)

        img_to_extract = ''
        for x in range(100, clip["frames"], segment_length):
            img_to_extract += '+eq(n\\,' + str(x) + ')'
        cmd = f'ffmpeg -i "{clip['path']}" -vf select="{img_to_extract},scale=640:360" -fps_mode passthrough "{TEMP_DIR.name}/thumbnail_%d.jpg"'
        result = subprocess.run(cmd,shell=True,stderr=subprocess.DEVNULL)

        # Compile clipSlate
        tell_user('Making clipSlate')
        imgs_path = []
        paste_coords = ((0, 360), (640, 360), (1280, 360), (0, 720), (640, 720), (1280, 720))

        for x in range(0,tot_stills):
            tmpImg = Image.open(TEMP_DIR.name + '/' + 'thumbnail_' + str(x+1) + '.jpg')
            slate.paste(tmpImg,paste_coords[x])

        # add text
        font_label = ImageFont.truetype('Arial Narrow.ttf', 50)
        font_title = ImageFont.truetype('Arial Narrow.ttf', 85)
        font_trt = ImageFont.truetype('Arial Narrow.ttf', 250)
        title_linebreaked = insert_newlines(clip['name'],25)
        if len(title_linebreaked) > 89:
            title_linebreaked = title_linebreaked[:92] +'...'
        draw = ImageDraw.Draw(slate)
        draw.text((96, 45), "title", font=font_label, fill='#666666')
        draw.text((1786, 45), "trt", font=font_label, fill='#666666')
        draw.text((1099, 52), clip["min_sec"], font=font_trt,fill='#FFBD00')
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
        final_slate.thumbnail((clip["width"], clip["height"]))
        final_slate = final_slate.convert("RGB")

        # Save the slate
        slate_path = TEMP_DIR.name + "/clipSlate.jpg"
        final_slate.save(slate_path, quality=95)

        # ==== Encode Clip
        tell_user('Transcoding video: ' + color.YELLOW + 'This might take a while. Please be patient!' + color.END, '')
        cmd = f'ffmpeg -y -i "{clip['path']}" -i "{slate_path}" -filter_complex "overlay=0:0:enable=\'between(t,0,.01)\'" -preset fast -c:a copy "{clip['directory']}/{clip['name']}_clipslate{clip['ext']}"'

        try:
            cmd_result = subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print('Please install ffmpeg + ffprobe. See: https://ffmpeg.org/download.html\n\n')
            shutdown()

        tell_user('clipSlate created successfully','success')
    else:
        tell_user(file + ' is not a video.','warn')
    pass

def insert_newlines(string, every=30):
    return '\n'.join(string[i:i+every] for i in range(0, len(string), every))    

def shutdown():
    TEMP_DIR.cleanup()
    sys.exit()

def main():
    # Setup args
    parser = argparse.ArgumentParser(description='Creates a slate and encodes it into frame 1 of the clip.')
    # parser.add_argument('-c', dest='onlyclip', action='store_true', help="Clip only. (Don't add it to the clip.)")
    parser.add_argument('path', help='The full path to a video or a folder containing multiple videos.')
    args = parser.parse_args()

    path = clean_path(args.path)

    # process args
    if args.path == None:
        parser.print_help()
        shutdown()

    show_header()

    type = path_type(path)

    if type =='file':
        # process a single clip
        process_clip(path)

    elif type =='dir':
        # process a directory of clips
        clips = get_clip_paths_from_dir(path)
        tell_user('Processing ' + str(len(clips)) + ' clips\n')
        for clip in clips:
            process_clip(clip)

    else:
        tell_user('Please provide a full path to a file or directory.','warn')



    shutdown()

if __name__ == "__main__":
    # Globals
    class color:
        PURPLE = '\033[95m'
        CYAN = '\033[96m'
        DARKCYAN = '\033[36m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
        ITALIC = '\033[3m'
        END = '\033[0m'
    
    TEMP_DIR = tempfile.TemporaryDirectory()

    main()